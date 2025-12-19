# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Idempotency Utilities for eBalance

Prevents duplicate API submissions by tracking idempotency keys.
Essential for financial report submissions where duplicates can cause issues.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, TypeVar, cast

import frappe
from frappe import _

T = TypeVar("T")


@dataclass
class IdempotencyResult:
    """Result of an idempotent operation"""
    is_duplicate: bool
    cached_result: Any | None = None
    idempotency_key: str | None = None
    original_timestamp: datetime | None = None


class IdempotencyManager:
    """
    Manages idempotency for API operations.
    
    Prevents duplicate submissions by storing results keyed by
    a hash of the operation parameters.
    
    Usage:
        manager = IdempotencyManager("ebalance")
        
        # Check if already processed
        key = manager.generate_key("submit_report", report_id="123")
        result = manager.check(key)
        if result.is_duplicate:
            return result.cached_result
        
        # Process and store
        response = submit_to_api()
        manager.store(key, response, ttl_hours=24)
    """
    
    def __init__(self, app_name: str = "ebalance"):
        self.app_name = app_name
        self.cache_prefix = f"idempotency:{app_name}"
    
    def generate_key(self, operation: str, **params) -> str:
        """
        Generate idempotency key from operation and parameters.
        
        Args:
            operation: Operation name (e.g., "submit_report")
            **params: Operation parameters
        
        Returns:
            Unique key for this operation + params combination
        """
        # Sort params for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_source = f"{operation}:{sorted_params}"
        
        # Generate short hash
        key_hash = hashlib.sha256(key_source.encode()).hexdigest()[:16]
        
        return f"{self.cache_prefix}:{operation}:{key_hash}"
    
    def check(self, key: str) -> IdempotencyResult:
        """
        Check if operation was already processed.
        
        Args:
            key: Idempotency key from generate_key()
        
        Returns:
            IdempotencyResult with duplicate status and cached result
        """
        cached = frappe.cache().get_value(key)
        
        if cached:
            return IdempotencyResult(
                is_duplicate=True,
                cached_result=cached.get("result"),
                idempotency_key=key,
                original_timestamp=datetime.fromisoformat(cached["timestamp"]) if cached.get("timestamp") else None
            )
        
        return IdempotencyResult(
            is_duplicate=False,
            idempotency_key=key
        )
    
    def store(self, key: str, result: Any, ttl_hours: int = 24):
        """
        Store operation result for idempotency checking.
        
        Args:
            key: Idempotency key
            result: Operation result to cache
            ttl_hours: Time to live in hours
        """
        data = {
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "app": self.app_name
        }
        
        frappe.cache().set_value(
            key,
            data,
            expires_in_sec=ttl_hours * 3600
        )
    
    def invalidate(self, key: str):
        """Remove idempotency key (allow re-processing)"""
        frappe.cache().delete_value(key)
    
    def get_or_execute(
        self,
        operation: str,
        func: Callable[..., T],
        ttl_hours: int = 24,
        **params
    ) -> tuple[T, bool]:
        """
        Execute function only if not already processed.
        
        Args:
            operation: Operation name
            func: Function to execute (receives **params)
            ttl_hours: Cache TTL
            **params: Parameters for both key generation and function
        
        Returns:
            Tuple of (result, was_cached)
        """
        key = self.generate_key(operation, **params)
        check_result = self.check(key)
        
        if check_result.is_duplicate:
            frappe.logger(self.app_name).info(
                f"Idempotency hit for {operation}, key={key[:50]}..."
            )
            return cast(T, check_result.cached_result), True
        
        # Execute function
        result = func(**params)
        
        # Store result
        self.store(key, result, ttl_hours)
        
        return result, False


# Singleton instance for eBalance
idempotency = IdempotencyManager("ebalance")


def idempotent(operation: str, ttl_hours: int = 24, key_params: list[str] | None = None):
    """
    Decorator to make a function idempotent.
    
    Usage:
        @idempotent("submit_report", ttl_hours=24, key_params=["report_id"])
        def submit_report(report_id, data):
            return api.submit(data)
    
    Args:
        operation: Operation name for key generation
        ttl_hours: Cache TTL
        key_params: List of parameter names to use for key (default: all params)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            # Build key params from function arguments
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Filter to specified params or use all
            if key_params:
                params = {k: v for k, v in bound.arguments.items() if k in key_params}
            else:
                params = dict(bound.arguments)
            
            # Check idempotency
            key = idempotency.generate_key(operation, **params)
            check_result = idempotency.check(key)
            
            if check_result.is_duplicate:
                frappe.logger("ebalance").info(
                    f"Idempotent operation '{operation}' already processed"
                )
                return cast(T, check_result.cached_result)
            
            # Execute
            result = func(*args, **kwargs)
            
            # Store
            idempotency.store(key, result, ttl_hours)
            
            return result
        
        return wrapper
    return decorator


# Document-based idempotency for audit trail

def get_submission_idempotency_key(doctype: str, docname: str, operation: str) -> str:
    """
    Generate idempotency key for document-based operations.
    
    Uses document modified timestamp to ensure re-submission after edits.
    """
    modified = frappe.db.get_value(doctype, docname, "modified")
    return idempotency.generate_key(
        operation,
        doctype=doctype,
        docname=docname,
        modified=str(modified)
    )


def check_report_submission(report_request_name: str) -> IdempotencyResult:
    """Check if eBalance report was already submitted"""
    key = get_submission_idempotency_key(
        "eBalance Report Request",
        report_request_name,
        "submit_report"
    )
    return idempotency.check(key)


def store_report_submission(report_request_name: str, result: dict):
    """Store successful report submission result"""
    key = get_submission_idempotency_key(
        "eBalance Report Request",
        report_request_name,
        "submit_report"
    )
    idempotency.store(key, result, ttl_hours=168)  # 7 days
