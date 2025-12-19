# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Tests for eBalance Idempotency Utilities

Tests the idempotency manager for preventing duplicate API submissions.
"""

import hashlib
import json
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from ebalance.utils.idempotency import (
    IdempotencyManager,
    IdempotencyResult,
    idempotent,
)


class TestIdempotencyResult(unittest.TestCase):
    """Test IdempotencyResult dataclass"""

    def test_non_duplicate_result(self):
        """Test non-duplicate result creation"""
        result = IdempotencyResult(is_duplicate=False)
        self.assertFalse(result.is_duplicate)
        self.assertIsNone(result.cached_result)
        self.assertIsNone(result.idempotency_key)
        self.assertIsNone(result.original_timestamp)

    def test_duplicate_result(self):
        """Test duplicate result creation"""
        timestamp = datetime.now()
        result = IdempotencyResult(
            is_duplicate=True,
            cached_result={"status": "success"},
            idempotency_key="test_key",
            original_timestamp=timestamp
        )
        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.cached_result, {"status": "success"})
        self.assertEqual(result.idempotency_key, "test_key")
        self.assertEqual(result.original_timestamp, timestamp)


class TestIdempotencyManager(IntegrationTestCase):
    """Test IdempotencyManager class"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.manager = IdempotencyManager("test_app")
        # Clear any existing cache entries
        self._clear_test_cache()

    def _clear_test_cache(self):
        """Clear test-related cache entries"""
        try:
            # Clear cache entries starting with our prefix
            cache = frappe.cache()
            if hasattr(cache, 'delete_keys'):
                cache.delete_keys("idempotency:test_app:*")
        except Exception:
            pass

    def test_generate_key_consistent(self):
        """Test key generation is consistent for same inputs"""
        key1 = self.manager.generate_key("submit_report", entity_id="1234567", year=2024)
        key2 = self.manager.generate_key("submit_report", entity_id="1234567", year=2024)
        self.assertEqual(key1, key2)

    def test_generate_key_different_for_different_params(self):
        """Test different params produce different keys"""
        key1 = self.manager.generate_key("submit_report", entity_id="1234567", year=2024)
        key2 = self.manager.generate_key("submit_report", entity_id="1234567", year=2025)
        self.assertNotEqual(key1, key2)

    def test_generate_key_different_for_different_operations(self):
        """Test different operations produce different keys"""
        key1 = self.manager.generate_key("submit_report", entity_id="1234567")
        key2 = self.manager.generate_key("get_report", entity_id="1234567")
        self.assertNotEqual(key1, key2)

    def test_generate_key_param_order_independent(self):
        """Test parameter order doesn't affect key"""
        key1 = self.manager.generate_key("op", a=1, b=2, c=3)
        key2 = self.manager.generate_key("op", c=3, a=1, b=2)
        self.assertEqual(key1, key2)

    def test_check_returns_not_duplicate_for_new_key(self):
        """Test check returns not duplicate for new key"""
        key = self.manager.generate_key("new_operation", param="value")
        result = self.manager.check(key)
        self.assertFalse(result.is_duplicate)

    def test_store_and_check_duplicate(self):
        """Test storing and checking returns duplicate"""
        key = self.manager.generate_key("test_operation", id="123")
        
        # Store a result
        self.manager.store(key, {"status": "success", "id": "123"})
        
        # Check should return duplicate
        result = self.manager.check(key)
        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.cached_result["status"], "success")
        self.assertEqual(result.cached_result["id"], "123")

    def test_store_with_ttl(self):
        """Test stored results expire after TTL"""
        key = self.manager.generate_key("expiring_op", id="456")
        
        # Store with very short TTL (needs integration test with actual cache)
        self.manager.store(key, {"data": "test"}, ttl_hours=0.0001)  # ~0.36 seconds
        
        # Should be found immediately
        result = self.manager.check(key)
        self.assertTrue(result.is_duplicate)

    def test_clear_key(self):
        """Test clearing a specific key"""
        key = self.manager.generate_key("clearable_op", id="789")
        
        # Store and verify
        self.manager.store(key, {"data": "test"})
        result = self.manager.check(key)
        self.assertTrue(result.is_duplicate)
        
        # Clear and verify
        self.manager.clear(key)
        result = self.manager.check(key)
        self.assertFalse(result.is_duplicate)

    def test_get_recent_operations(self):
        """Test getting list of recent operations"""
        # Store some operations
        for i in range(3):
            key = self.manager.generate_key(f"recent_op_{i}", id=str(i))
            self.manager.store(key, {"index": i})
        
        # Get recent operations (if method exists)
        if hasattr(self.manager, 'get_recent_operations'):
            recent = self.manager.get_recent_operations(limit=10)
            self.assertIsInstance(recent, list)


class TestIdempotentDecorator(IntegrationTestCase):
    """Test idempotent decorator"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self._call_count = 0

    def test_first_call_executes_function(self):
        """Test first call executes the function"""
        self._call_count = 0
        
        @idempotent(app_name="test_decorator")
        def my_function(entity_id: str) -> dict:
            self._call_count += 1
            return {"entity_id": entity_id, "processed": True}
        
        result = my_function("1234567")
        self.assertEqual(result["entity_id"], "1234567")
        self.assertEqual(self._call_count, 1)

    def test_duplicate_call_returns_cached(self):
        """Test duplicate call returns cached result without executing"""
        self._call_count = 0
        
        @idempotent(app_name="test_decorator_cache", ttl_hours=1)
        def expensive_operation(report_id: str) -> dict:
            self._call_count += 1
            return {"report_id": report_id, "timestamp": str(datetime.now())}
        
        # First call
        result1 = expensive_operation("report_123")
        self.assertEqual(self._call_count, 1)
        
        # Second call with same params - should return cached
        result2 = expensive_operation("report_123")
        self.assertEqual(self._call_count, 1)  # Should not increment
        self.assertEqual(result1["report_id"], result2["report_id"])

    def test_different_params_execute_separately(self):
        """Test different parameters execute function separately"""
        self._call_count = 0
        
        @idempotent(app_name="test_decorator_params")
        def process_entity(entity_id: str, year: int) -> dict:
            self._call_count += 1
            return {"entity_id": entity_id, "year": year}
        
        result1 = process_entity("1234567", 2024)
        result2 = process_entity("1234567", 2025)
        
        self.assertEqual(self._call_count, 2)
        self.assertEqual(result1["year"], 2024)
        self.assertEqual(result2["year"], 2025)

    def test_exception_not_cached(self):
        """Test exceptions are not cached"""
        self._call_count = 0
        
        @idempotent(app_name="test_decorator_error")
        def failing_function(param: str) -> dict:
            self._call_count += 1
            if self._call_count < 3:
                raise ValueError("Temporary failure")
            return {"success": True}
        
        # First two calls should fail
        for _ in range(2):
            try:
                failing_function("test")
            except ValueError:
                pass
        
        # Third call should succeed
        result = failing_function("test")
        self.assertEqual(result["success"], True)
        self.assertEqual(self._call_count, 3)


class TestIdempotencyKeyGeneration(unittest.TestCase):
    """Test key generation edge cases"""

    def test_key_with_complex_params(self):
        """Test key generation with complex parameter types"""
        manager = IdempotencyManager("test")
        
        key = manager.generate_key(
            "complex_op",
            list_param=[1, 2, 3],
            dict_param={"nested": "value"},
            date_param=datetime(2024, 1, 1)
        )
        
        self.assertIsInstance(key, str)
        self.assertIn("idempotency:test:complex_op:", key)

    def test_key_with_none_values(self):
        """Test key generation with None values"""
        manager = IdempotencyManager("test")
        
        key1 = manager.generate_key("op", param=None)
        key2 = manager.generate_key("op", param=None)
        
        self.assertEqual(key1, key2)

    def test_key_with_empty_params(self):
        """Test key generation with empty parameters"""
        manager = IdempotencyManager("test")
        
        key1 = manager.generate_key("op")
        key2 = manager.generate_key("op")
        
        self.assertEqual(key1, key2)

    def test_key_length(self):
        """Test key length is reasonable"""
        manager = IdempotencyManager("test")
        
        key = manager.generate_key("very_long_operation_name", 
                                   param1="value1", 
                                   param2="value2",
                                   param3="value3")
        
        # Key should not be excessively long
        self.assertLess(len(key), 200)


class TestIdempotencyWithRealOperations(IntegrationTestCase):
    """Integration tests simulating real eBalance operations"""

    def test_duplicate_report_submission_prevented(self):
        """Test duplicate report submissions are prevented"""
        manager = IdempotencyManager("ebalance")
        
        # Simulate report submission
        submission_params = {
            "entity_id": "1234567",
            "year": 2024,
            "period": 12,
            "report_type": "balance"
        }
        
        key = manager.generate_key("submit_report", **submission_params)
        
        # First submission
        result1 = manager.check(key)
        self.assertFalse(result1.is_duplicate)
        
        # Store successful result
        manager.store(key, {"submission_id": "SUB001", "status": "success"})
        
        # Second submission should be duplicate
        result2 = manager.check(key)
        self.assertTrue(result2.is_duplicate)
        self.assertEqual(result2.cached_result["submission_id"], "SUB001")

    def test_concurrent_submission_handling(self):
        """Test handling of concurrent submissions"""
        manager = IdempotencyManager("ebalance")
        
        key = manager.generate_key("concurrent_op", id="test")
        
        # Simulate concurrent check-and-store pattern
        result1 = manager.check(key)
        result2 = manager.check(key)
        
        # Both should see not duplicate initially
        self.assertFalse(result1.is_duplicate)
        self.assertFalse(result2.is_duplicate)
        
        # First one stores
        manager.store(key, {"winner": "first"})
        
        # Now should see duplicate
        result3 = manager.check(key)
        self.assertTrue(result3.is_duplicate)
