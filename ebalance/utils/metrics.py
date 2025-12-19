# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Metrics and Telemetry for eBalance

Collects operational metrics for monitoring and observability.
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import frappe


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: dict = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and stores metrics for eBalance operations.
    
    Metrics are stored in Redis with TTL for automatic cleanup.
    
    Usage:
        metrics = MetricsCollector()
        
        # Increment counter
        metrics.increment("api_calls", tags={"endpoint": "submit_report"})
        
        # Record timing
        with metrics.timer("api_latency", tags={"endpoint": "submit_report"}):
            response = api.call()
        
        # Record gauge
        metrics.gauge("queue_size", 42)
    """
    
    CACHE_PREFIX = "metrics:ebalance"
    DEFAULT_TTL = 86400  # 24 hours
    
    def increment(self, name: str, value: float = 1, tags: dict | None = None):
        """Increment a counter metric"""
        key = self._make_key(name, tags)
        try:
            current = frappe.cache().get_value(key) or 0
            frappe.cache().set_value(key, current + value, expires_in_sec=self.DEFAULT_TTL)
        except Exception:
            pass  # Fail silently - metrics should not break the app
    
    def gauge(self, name: str, value: float, tags: dict | None = None):
        """Set a gauge metric"""
        key = self._make_key(name, tags)
        data = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            frappe.cache().set_value(key, data, expires_in_sec=self.DEFAULT_TTL)
        except Exception:
            pass
    
    def timing(self, name: str, duration_ms: float, tags: dict | None = None):
        """Record a timing metric"""
        key = self._make_key(f"{name}:timings", tags)
        try:
            timings = frappe.cache().get_value(key) or []
            timings.append({
                "value": duration_ms,
                "timestamp": datetime.utcnow().isoformat()
            })
            # Keep last 100 timings
            timings = timings[-100:]
            frappe.cache().set_value(key, timings, expires_in_sec=self.DEFAULT_TTL)
        except Exception:
            pass
    
    @contextmanager
    def timer(self, name: str, tags: dict | None = None):
        """Context manager for timing operations"""
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000
            self.timing(name, duration_ms, tags)
    
    def _make_key(self, name: str, tags: dict | None = None) -> str:
        """Generate cache key for metric"""
        key = f"{self.CACHE_PREFIX}:{name}"
        if tags:
            tag_str = ":".join(f"{k}={v}" for k, v in sorted(tags.items()))
            key = f"{key}:{tag_str}"
        return key
    
    def get_counter(self, name: str, tags: dict | None = None) -> float:
        """Get current counter value"""
        key = self._make_key(name, tags)
        return frappe.cache().get_value(key) or 0
    
    def get_gauge(self, name: str, tags: dict | None = None) -> dict | None:
        """Get current gauge value"""
        key = self._make_key(name, tags)
        return frappe.cache().get_value(key)
    
    def get_timing_stats(self, name: str, tags: dict | None = None) -> dict:
        """Get timing statistics"""
        key = self._make_key(f"{name}:timings", tags)
        timings = frappe.cache().get_value(key) or []
        
        if not timings:
            return {"count": 0}
        
        values = [t["value"] for t in timings]
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }
    
    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


# Singleton instance
metrics = MetricsCollector()


# Pre-defined metric helpers for eBalance

def record_api_call(endpoint: str, success: bool, duration_ms: float):
    """Record an API call metric"""
    metrics.increment("api_calls_total", tags={"endpoint": endpoint})
    if success:
        metrics.increment("api_calls_success", tags={"endpoint": endpoint})
    else:
        metrics.increment("api_calls_failed", tags={"endpoint": endpoint})
    metrics.timing("api_latency", duration_ms, tags={"endpoint": endpoint})


def record_report_submission(report_type: str, success: bool):
    """Record report submission metric"""
    metrics.increment("reports_submitted_total", tags={"type": report_type})
    if success:
        metrics.increment("reports_submitted_success", tags={"type": report_type})
    else:
        metrics.increment("reports_submitted_failed", tags={"type": report_type})


def record_error(error_type: str, endpoint: str | None = None):
    """Record an error metric"""
    tags = {"type": error_type}
    if endpoint:
        tags["endpoint"] = endpoint
    metrics.increment("errors_total", tags=tags)


@frappe.whitelist()
def get_metrics_summary():
    """Get metrics summary for monitoring dashboard"""
    frappe.only_for(["System Manager", "Administrator"])
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "api_calls": {
            "total": metrics.get_counter("api_calls_total"),
            "success": metrics.get_counter("api_calls_success"),
            "failed": metrics.get_counter("api_calls_failed")
        },
        "reports": {
            "submitted": metrics.get_counter("reports_submitted_total"),
            "success": metrics.get_counter("reports_submitted_success"),
            "failed": metrics.get_counter("reports_submitted_failed")
        },
        "latency": metrics.get_timing_stats("api_latency"),
        "errors": metrics.get_counter("errors_total")
    }
