# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Health Check API for eBalance

Provides endpoints for monitoring eBalance app health and connectivity.
"""

from datetime import datetime
from typing import Any

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def health():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Health status with timestamp
    
    Example:
        GET /api/method/ebalance.api.health.health
        
        Response: {
            "status": "healthy",
            "app": "ebalance",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    return {
        "status": "healthy",
        "app": "ebalance",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@frappe.whitelist()
def detailed_health():
    """
    Detailed health check with dependency status.
    
    Requires authentication. Checks:
    - Database connectivity
    - Redis/cache connectivity
    - eBalance API settings
    - External API reachability (optional)
    
    Returns:
        dict: Detailed health status
    """
    frappe.only_for(["System Manager", "Administrator"])
    
    checks: dict[str, Any] = {
        "status": "healthy",
        "app": "ebalance",
        "version": get_app_version(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {}
    }
    
    # Database check
    checks["checks"]["database"] = check_database()
    
    # Cache check
    checks["checks"]["cache"] = check_cache()
    
    # Settings check
    checks["checks"]["settings"] = check_settings()
    
    # Circuit breaker status
    checks["checks"]["circuit_breaker"] = check_circuit_breaker()
    
    # Overall status
    all_healthy = all(
        c.get("status") == "healthy" 
        for c in checks["checks"].values()
    )
    checks["status"] = "healthy" if all_healthy else "degraded"
    
    return checks


@frappe.whitelist()
def check_api_connectivity():
    """
    Test connectivity to MOF eBalance API.
    
    Requires authentication.
    
    Returns:
        dict: API connectivity status
    """
    frappe.only_for(["System Manager", "Administrator"])
    
    result = {
        "status": "unknown",
        "response_time_ms": None,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        import time
        
        # Get settings
        settings = frappe.get_single("eBalance Settings")
        if not getattr(settings, "enabled", False):
            result["status"] = "disabled"
            result["error"] = "eBalance integration is disabled"
            return result
        
        # Test API endpoint
        start_time = time.time()
        
        # Try a simple API call (e.g., get entity info)
        # This is a placeholder - adjust based on actual eBalance API
        from ebalance.api_client import EBalanceClient
        client = EBalanceClient()
        
        # Use a lightweight endpoint for health check
        # Most APIs have a /ping or /health endpoint
        response = client.test_connection()
        
        end_time = time.time()
        result["response_time_ms"] = round((end_time - start_time) * 1000, 2)
        result["status"] = "healthy" if response else "unhealthy"
        
    except ImportError:
        result["status"] = "error"
        result["error"] = "eBalance client not available"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return result


def get_app_version() -> str:
    """Get eBalance app version"""
    try:
        return frappe.get_attr("ebalance.__version__")
    except AttributeError:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=frappe.get_app_path("ebalance"),
                capture_output=True,
                text=True
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"


def check_database() -> dict:
    """Check database connectivity"""
    try:
        frappe.db.sql("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_cache() -> dict:
    """Check Redis/cache connectivity"""
    try:
        test_key = "ebalance:health_check"
        frappe.cache().set_value(test_key, "ok", expires_in_sec=60)
        value = frappe.cache().get_value(test_key)
        if value == "ok":
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "Cache read/write mismatch"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_settings() -> dict:
    """Check eBalance settings configuration"""
    try:
        settings = frappe.get_single("eBalance Settings")
        
        issues = []
        enabled = getattr(settings, "enabled", False)
        api_url = getattr(settings, "api_url", None)
        if not enabled:
            issues.append("Integration disabled")
        if not api_url:
            issues.append("API URL not configured")
        if not settings.get_password("api_key"):
            issues.append("API key not configured")
        
        if issues:
            return {
                "status": "warning" if enabled else "disabled",
                "issues": issues
            }
        
        return {"status": "healthy"}
    except frappe.DoesNotExistError:
        return {"status": "unhealthy", "error": "Settings not found"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_circuit_breaker() -> dict:
    """Check circuit breaker status"""
    try:
        from ebalance.utils.resilience import ebalance_circuit_breaker
        
        cb = ebalance_circuit_breaker
        return {
            "status": "healthy" if cb.state.value == "closed" else "degraded",
            "state": cb.state.value,
            "failure_count": getattr(cb, "failure_count", 0),
            "last_failure": getattr(cb, "last_failure_time", None)
        }
    except ImportError:
        return {"status": "unknown", "error": "Resilience module not available"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@frappe.whitelist()
def readiness():
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if app is ready to serve traffic.
    """
    try:
        # Check critical dependencies
        frappe.db.sql("SELECT 1")
        
        settings = frappe.get_single("eBalance Settings")
        if getattr(settings, "enabled", False) and not getattr(settings, "api_url", None):
            frappe.throw("Not ready: API URL not configured")
        
        return {"ready": True}
    except Exception as e:
        frappe.local.response.http_status_code = 503
        return {"ready": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def liveness():
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if app process is alive.
    """
    return {"alive": True, "timestamp": datetime.utcnow().isoformat() + "Z"}
