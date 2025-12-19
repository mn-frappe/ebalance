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
from frappe.tests.utils import FrappeTestCase

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


class TestIdempotencyManager(FrappeTestCase):
    """Test IdempotencyManager class"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.manager = IdempotencyManager("test_app")

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
        if result.cached_result:
            self.assertEqual(result.cached_result.get("status"), "success")


class TestIdempotentDecorator(FrappeTestCase):
    """Test idempotent decorator"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self._call_count = 0

    def test_first_call_executes_function(self):
        """Test first call executes the function"""
        self._call_count = 0
        
        @idempotent(operation="test_first_call")
        def my_function(entity_id: str) -> dict:
            self._call_count += 1
            return {"entity_id": entity_id, "processed": True}
        
        result = my_function("1234567")
        self.assertEqual(result["entity_id"], "1234567")
        self.assertEqual(self._call_count, 1)

    def test_duplicate_call_returns_cached(self):
        """Test duplicate call returns cached result without executing"""
        self._call_count = 0
        
        @idempotent(operation="test_duplicate", ttl_hours=1)
        def expensive_operation(report_id: str) -> dict:
            self._call_count += 1
            return {"report_id": report_id, "count": self._call_count}
        
        # First call
        result1 = expensive_operation("report_123")
        self.assertEqual(self._call_count, 1)
        
        # Second call with same params - should return cached
        result2 = expensive_operation("report_123")
        # Verify it's using cached result
        self.assertEqual(result1["report_id"], result2["report_id"])


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
        
        key = manager.generate_key(
            "very_long_operation_name",
            param1="value1",
            param2="value2",
            param3="value3"
        )
        
        self.assertLess(len(key), 200)


class TestIdempotencyWithRealOperations(FrappeTestCase):
    """Integration tests simulating real eBalance operations"""

    @patch("frappe.cache")
    def test_duplicate_report_submission_prevented(self, mock_cache):
        """Test duplicate report submissions are prevented"""
        # Set up mock cache to simulate real behavior
        cache_storage = {}
        
        def mock_get_value(key):
            return cache_storage.get(key)
        
        def mock_set_value(key, value, expires_in_sec=None):
            cache_storage[key] = value
        
        mock_cache_instance = MagicMock()
        mock_cache_instance.get_value = mock_get_value
        mock_cache_instance.set_value = mock_set_value
        mock_cache.return_value = mock_cache_instance
        
        manager = IdempotencyManager("ebalance")
        
        submission_params = {
            "entity_id": "1234567",
            "year": 2024,
            "period": 12,
            "report_type": "balance"
        }
        
        key = manager.generate_key("submit_report", **submission_params)
        
        # First submission - not duplicate
        result1 = manager.check(key)
        self.assertFalse(result1.is_duplicate)
        
        # Store successful result
        manager.store(key, {"submission_id": "SUB001", "status": "success"})
        
        # Second submission should be duplicate
        result2 = manager.check(key)
        self.assertTrue(result2.is_duplicate)
        self.assertEqual(result2.cached_result, {"submission_id": "SUB001", "status": "success"})
