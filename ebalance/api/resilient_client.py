# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Resilient HTTP Client Wrapper for eBalance

Wraps the existing HTTP client with:
- Circuit breaker integration
- Structured logging with correlation IDs
- Metrics collection
- Enhanced error handling
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe

from ebalance.api.http_client import EBalanceHTTPClient, EBalanceHTTPError


class ResilientEBalanceClient:
    """
    Resilient wrapper for EBalanceHTTPClient.
    
    Adds:
    - Circuit breaker for fault tolerance
    - Structured logging with correlation IDs
    - Metrics collection for monitoring
    - Enhanced error categorization
    
    Usage:
        client = ResilientEBalanceClient()
        
        # Simple usage
        result = client.get("/api/entity/info")
        
        # With correlation ID for tracing
        with client.traced("submit_report") as ctx:
            result = ctx.post("/api/reports", json=report_data)
    """
    
    def __init__(self, settings=None):
        self._inner_client = EBalanceHTTPClient(settings)
        self._circuit_breaker = None
        self._logger = None
        self._metrics = None
    
    @property
    def circuit_breaker(self):
        """Lazy load circuit breaker"""
        if self._circuit_breaker is None:
            try:
                from ebalance.utils.resilience import ebalance_circuit_breaker
                self._circuit_breaker = ebalance_circuit_breaker
            except ImportError:
                self._circuit_breaker = None
        return self._circuit_breaker
    
    @property
    def logger(self):
        """Lazy load structured logger"""
        if self._logger is None:
            try:
                from ebalance.utils.logging import get_logger
                self._logger = get_logger()
            except ImportError:
                self._logger = None
        return self._logger
    
    @property
    def metrics(self):
        """Lazy load metrics collector"""
        if self._metrics is None:
            try:
                from ebalance.utils.metrics import metrics
                self._metrics = metrics
            except ImportError:
                self._metrics = None
        return self._metrics
    
    def _categorize_error(self, error: Exception) -> str:
        """Categorize error for metrics"""
        if isinstance(error, EBalanceHTTPError):
            status = error.status_code or 0
            if status == 408:
                return "timeout"
            elif status == 429:
                return "rate_limited"
            elif status == 503:
                return "service_unavailable"
            elif status >= 500:
                return "server_error"
            elif status >= 400:
                return "client_error"
        return "unknown"
    
    def _execute_with_resilience(self, operation: str, func, *args, **kwargs) -> Any:
        """Execute function with circuit breaker and metrics"""
        
        # Log request
        if self.logger:
            self.logger.info(
                f"eBalance API call: {operation}",
                extra={"operation": operation, "endpoint": args[0] if args else None}
            )
        
        # Track metrics
        error_type = None
        
        try:
            # Execute with circuit breaker if available
            if self.circuit_breaker:
                result = self.circuit_breaker.call(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success metrics
            if self.metrics:
                self.metrics.increment("ebalance_api_requests", tags={"operation": operation, "status": "success"})
            
            return result
            
        except Exception as e:
            error_type = self._categorize_error(e)
            
            # Log error
            if self.logger:
                self.logger.error(
                    f"eBalance API error: {operation}",
                    extra={"operation": operation, "error_type": error_type, "error": str(e)}
                )
            
            # Record error metrics
            if self.metrics:
                self.metrics.increment("ebalance_api_requests", tags={"operation": operation, "status": "error"})
                self.metrics.increment("ebalance_api_errors", tags={"operation": operation, "error_type": error_type})
            
            raise
    
    @contextmanager
    def traced(self, operation: str):
        """
        Context manager for traced API calls.
        
        Usage:
            with client.traced("submit_report") as ctx:
                result = ctx.post("/api/reports", json=data)
        """
        # Set correlation ID if logger available
        correlation_id = None
        if self.logger:
            import uuid
            correlation_id = str(uuid.uuid4())[:8]
            frappe.local.correlation_id = correlation_id
        
        # Start timing
        import time
        start_time = time.time()
        
        try:
            yield self
        finally:
            # Record timing
            duration = time.time() - start_time
            if self.metrics:
                self.metrics.timing(f"ebalance_api_duration_{operation}", duration)
            
            # Clean up correlation ID
            if correlation_id and hasattr(frappe.local, "correlation_id"):
                delattr(frappe.local, "correlation_id")
    
    def get(self, endpoint: str, auth_header=None, **kwargs) -> dict:
        """Make GET request with resilience"""
        return self._execute_with_resilience(
            "get",
            self._inner_client.get,
            endpoint,
            auth_header,
            **kwargs
        )
    
    def post(self, endpoint: str, auth_header=None, **kwargs) -> dict:
        """Make POST request with resilience"""
        return self._execute_with_resilience(
            "post",
            self._inner_client.post,
            endpoint,
            auth_header,
            **kwargs
        )
    
    def request(self, method: str, endpoint: str, auth_header=None, **kwargs) -> dict:
        """Make request with resilience"""
        return self._execute_with_resilience(
            method.lower(),
            self._inner_client.request,
            method,
            endpoint,
            auth_header,
            **kwargs
        )
    
    def close(self):
        """Close underlying client"""
        self._inner_client.close()
    
    # Expose inner client properties
    @property
    def base_url(self):
        return self._inner_client.base_url
    
    @property
    def settings(self):
        return self._inner_client.settings


def get_resilient_client(settings=None) -> ResilientEBalanceClient:
    """Get resilient eBalance HTTP client"""
    return ResilientEBalanceClient(settings)


# Convenience function for one-off requests
def resilient_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make a resilient API request"""
    client = get_resilient_client()
    try:
        return client.request(method, endpoint, **kwargs)
    finally:
        client.close()
