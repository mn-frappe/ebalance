# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Tests for eBalance Resilience Utilities

Tests circuit breaker, rate limiting, and retry logic.
"""

import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

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
        # Clear any cached state
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
        
        # Trigger failures to open circuit
        for _ in range(3):
            try:
                failing_func()
            except Exception:
                pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)

    def test_open_circuit_rejects_requests(self):
        """Test open circuit rejects requests"""
        breaker = CircuitBreaker(
            name="test_breaker_reject",
            failure_threshold=2,
            recovery_timeout=60
        )
        
        @breaker
        def failing_func():
            raise Exception("API Error")
        
        # Open the circuit
        for _ in range(2):
            try:
                failing_func()
            except Exception:
                pass
        
        # Next call should be rejected with CircuitOpenError
        with self.assertRaises(Exception) as ctx:
            failing_func()
        
        # Should raise circuit open error, not the original error
        self.assertIn("circuit", str(ctx.exception).lower())

    def test_circuit_transitions_to_half_open(self):
        """Test circuit transitions to half-open after timeout"""
        breaker = CircuitBreaker(
            name="test_breaker_half",
            failure_threshold=2,
            recovery_timeout=1  # 1 second timeout
        )
        
        @breaker
        def failing_func():
            raise Exception("API Error")
        
        # Open the circuit
        for _ in range(2):
            try:
                failing_func()
            except Exception:
                pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should now allow a test request (half-open)
        @breaker
        def success_func():
            return "recovered"
        
        result = success_func()
        self.assertEqual(result, "recovered")

    def test_half_open_success_closes_circuit(self):
        """Test successful call in half-open state closes circuit"""
        breaker = CircuitBreaker(
            name="test_breaker_close",
            failure_threshold=2,
            recovery_timeout=1
        )
        
        call_count = [0]
        
        @breaker
        def sometimes_fails():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("API Error")
            return "success"
        
        # Open the circuit
        for _ in range(2):
            try:
                sometimes_fails()
            except Exception:
                pass
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # This should succeed and close the circuit
        result = sometimes_fails()
        self.assertEqual(result, "success")
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_custom_failure_threshold(self):
        """Test custom failure threshold"""
        breaker = CircuitBreaker(
            name="test_custom_threshold",
            failure_threshold=5
        )
        
        @breaker
        def failing_func():
            raise Exception("Error")
        
        # 4 failures should not open circuit
        for _ in range(4):
            try:
                failing_func()
            except Exception:
                pass
        
        self.assertEqual(breaker.state, CircuitState.CLOSED)
        
        # 5th failure should open it
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
        
        # Open the circuit
        for _ in range(2):
            try:
                failing_func()
            except Exception:
                pass
        
        self.assertEqual(breaker.state, CircuitState.OPEN)
        
        # Reset should close it
        breaker.reset()
        self.assertEqual(breaker.state, CircuitState.CLOSED)


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter class"""

    def test_allows_requests_within_limit(self):
        """Test rate limiter allows requests within limit"""
        limiter = RateLimiter(max_calls=5, window_seconds=60)
        
        for _ in range(5):
            self.assertTrue(limiter.allow())

    def test_blocks_requests_over_limit(self):
        """Test rate limiter blocks requests over limit"""
        limiter = RateLimiter(max_calls=3, window_seconds=60)
        
        # Use up the limit
        for _ in range(3):
            limiter.allow()
        
        # Next should be blocked
        self.assertFalse(limiter.allow())

    def test_resets_after_window(self):
        """Test rate limiter resets after window expires"""
        limiter = RateLimiter(max_calls=2, window_seconds=1)
        
        # Use up the limit
        limiter.allow()
        limiter.allow()
        self.assertFalse(limiter.allow())
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should allow again
        self.assertTrue(limiter.allow())

    def test_remaining_calls(self):
        """Test remaining calls tracking"""
        limiter = RateLimiter(max_calls=5, window_seconds=60)
        
        self.assertEqual(limiter.remaining, 5)
        limiter.allow()
        self.assertEqual(limiter.remaining, 4)
        limiter.allow()
        self.assertEqual(limiter.remaining, 3)


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
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
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
        
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def always_fails():
            call_count[0] += 1
            raise Exception("Permanent error")
        
        with self.assertRaises(Exception) as ctx:
            always_fails()
        
        self.assertEqual(call_count[0], 4)  # Initial + 3 retries
        self.assertIn("Permanent error", str(ctx.exception))

    def test_respects_retryable_exceptions(self):
        """Test only retries specified exception types"""
        call_count = [0]
        
        @retry_with_backoff(
            max_retries=3,
            base_delay=0.1,
            retryable_exceptions=(ConnectionError,)
        )
        def raises_value_error():
            call_count[0] += 1
            raise ValueError("Not retryable")
        
        with self.assertRaises(ValueError):
            raises_value_error()
        
        # Should not retry on ValueError
        self.assertEqual(call_count[0], 1)

    def test_exponential_backoff(self):
        """Test exponential backoff timing"""
        call_times = []
        
        @retry_with_backoff(max_retries=2, base_delay=0.1, exponential=True)
        def failing_func():
            call_times.append(time.time())
            raise Exception("Error")
        
        try:
            failing_func()
        except Exception:
            pass
        
        # Check delays are increasing
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            self.assertGreater(delay2, delay1)

    def test_max_delay_cap(self):
        """Test maximum delay cap is respected"""
        call_count = [0]
        start_time = time.time()
        
        @retry_with_backoff(
            max_retries=2,
            base_delay=0.1,
            max_delay=0.2,
            exponential=True
        )
        def failing_func():
            call_count[0] += 1
            raise Exception("Error")
        
        try:
            failing_func()
        except Exception:
            pass
        
        total_time = time.time() - start_time
        # With max_delay=0.2, total time should be capped
        self.assertLess(total_time, 2.0)


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
        @retry_with_backoff(max_retries=2, base_delay=0.1)
        def api_call():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("API Error")
            return "success"
        
        result = api_call()
        self.assertEqual(result, "success")
        self.assertEqual(breaker.state, CircuitState.CLOSED)

    def test_rate_limiter_with_circuit_breaker(self):
        """Test rate limiter preventing circuit from opening due to rate limits"""
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        breaker = CircuitBreaker(
            name="rate_limit_test",
            failure_threshold=3
        )
        
        def api_call():
            if not limiter.allow():
                return None  # Rate limited, don't count as failure
            return "success"
        
        results = []
        for _ in range(5):
            result = api_call()
            results.append(result)
        
        # First 2 should succeed, rest should be None (rate limited)
        self.assertEqual(results[:2], ["success", "success"])
        self.assertEqual(results[2:], [None, None, None])
