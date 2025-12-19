# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Tests for eBalance Resilience Utilities

Tests circuit breaker and retry logic.
"""

import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ebalance.utils.resilience import (
    CircuitBreaker,
    CircuitState,
    RateLimiter,
    retry_with_backoff,
)


class TestCircuitState(unittest.TestCase):
    """Test CircuitState enum"""

    def test_circuit_states_exist(self):
        """Test all circuit states are defined"""
        self.assertEqual(CircuitState.CLOSED.value, "closed")
        self.assertEqual(CircuitState.OPEN.value, "open")
        self.assertEqual(CircuitState.HALF_OPEN.value, "half_open")


class TestCircuitBreaker(unittest.TestCase):
    """Test CircuitBreaker class"""

    def setUp(self):
        """Set up test fixtures"""
        try:
            frappe.cache().delete_value("circuit_breaker:test_breaker")
        except Exception:
            pass

    def test_initial_state_is_closed(self):
        """Test circuit breaker starts in closed state"""
        breaker = CircuitBreaker(name="test_breaker")
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_successful_call_keeps_closed(self):
        """Test successful call keeps circuit closed"""
        breaker = CircuitBreaker(name="test_breaker", failure_threshold=3)
        
        @breaker
        def success_func():
            return "success"
        
        result = success_func()
        self.assertEqual(result, "success")
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold"""
        breaker = CircuitBreaker(
            name="test_breaker_open",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        @breaker
        def failing_func():
            raise Exception("API Error")
        
        for _ in range(3):
            try:
                failing_func()
            except Exception:
                pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)

    def test_custom_failure_threshold(self):
        """Test custom failure threshold"""
        breaker = CircuitBreaker(
            name="test_custom_threshold",
            failure_threshold=5
        )
        
        @breaker
        def failing_func():
            raise Exception("Error")
        
        for _ in range(4):
            try:
                failing_func()
            except Exception:
                pass
        
        self.assertEqual(breaker.state, CircuitState.CLOSED)
        
        try:
            failing_func()
        except Exception:
            pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)

    def test_reset_method(self):
        """Test manual reset of circuit breaker"""
        breaker = CircuitBreaker(
            name="test_reset",
            failure_threshold=2
        )
        
        @breaker
        def failing_func():
            raise Exception("Error")
        
        for _ in range(2):
            try:
                failing_func()
            except Exception:
                pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)
        
        breaker.reset()
        self.assertEqual(breaker.state, CircuitState.CLOSED)


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter class"""

    def test_rate_limiter_creation(self):
        """Test rate limiter can be created"""
        limiter = RateLimiter(name="test_limiter", calls=5, period=60)
        self.assertEqual(limiter.name, "test_limiter")
        self.assertEqual(limiter.calls, 5)
        self.assertEqual(limiter.period, 60)

    def test_acquire_within_limit(self):
        """Test acquiring tokens within limit"""
        limiter = RateLimiter(name="test_acquire", calls=5, period=60)
        
        # Should be able to acquire
        result = limiter.acquire(blocking=False)
        self.assertTrue(result)

    def test_rate_limiter_as_decorator(self):
        """Test rate limiter works as decorator"""
        limiter = RateLimiter(name="test_decorator", calls=100, period=60)
        
        @limiter
        def api_call():
            return "success"
        
        result = api_call()
        self.assertEqual(result, "success")


class TestRetryWithBackoff(unittest.TestCase):
    """Test retry_with_backoff decorator"""

    def test_successful_call_no_retry(self):
        """Test successful call doesn't retry"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=3)
        def success_func():
            call_count[0] += 1
            return "success"
        
        result = success_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 1)

    def test_retries_on_failure(self):
        """Test function retries on failure"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def eventually_succeeds():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary error")
            return "success"
        
        result = eventually_succeeds()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)

    def test_gives_up_after_max_retries(self):
        """Test gives up after max retries"""
        call_count = [0]
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def always_fails():
            call_count[0] += 1
            raise Exception("Permanent error")
        
        with self.assertRaises(Exception) as ctx:
            always_fails()
        
        self.assertEqual(call_count[0], 4)  # Initial + 3 retries
        self.assertIn("Permanent error", str(ctx.exception))

    def test_respects_exception_types(self):
        """Test only retries specified exception types"""
        call_count = [0]
        
        @retry_with_backoff(
            max_retries=3,
            initial_delay=0.1,
            exceptions=(ConnectionError,)
        )
        def raises_value_error():
            call_count[0] += 1
            raise ValueError("Not retryable")
        
        with self.assertRaises(ValueError):
            raises_value_error()
        
        self.assertEqual(call_count[0], 1)

    def test_on_retry_callback(self):
        """Test on_retry callback is called"""
        retry_calls = []
        
        def on_retry_callback(exc, attempt):
            retry_calls.append((str(exc), attempt))
        
        @retry_with_backoff(
            max_retries=2,
            initial_delay=0.1,
            on_retry=on_retry_callback
        )
        def failing_func():
            raise Exception("Test error")
        
        try:
            failing_func()
        except Exception:
            pass
        
        self.assertEqual(len(retry_calls), 2)


class TestResilienceIntegration(unittest.TestCase):
    """Integration tests for resilience utilities"""

    def test_circuit_breaker_with_retry(self):
        """Test circuit breaker combined with retry"""
        breaker = CircuitBreaker(
            name="integration_test",
            failure_threshold=5,
            recovery_timeout=60
        )
        
        call_count = [0]
        
        @breaker
        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def api_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("API Error")
            return "success"
        
        result = api_call()
        self.assertEqual(result, "success")
        self.assertEqual(breaker.state, CircuitState.CLOSED)
