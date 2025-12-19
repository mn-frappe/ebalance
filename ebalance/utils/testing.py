# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Test Utilities for eBalance

Provides mock fixtures, test helpers, and factory functions for testing.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import frappe


@dataclass
class MockResponse:
    """Mock HTTP response"""
    status_code: int = 200
    content: bytes | str = b""
    headers: dict = field(default_factory=dict)
    text: str = field(init=False, default="")
    
    def __post_init__(self):
        if isinstance(self.content, str):
            self.content = self.content.encode("utf-8")
        self.text = bytes(self.content).decode("utf-8")
    
    def json(self) -> dict:
        return json.loads(self.content)
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class EBalanceMockClient:
    """
    Mock eBalance API client for testing.
    
    Usage:
        with EBalanceMockClient() as mock_client:
            mock_client.set_response("submit_report", {"success": True, "id": "123"})
            
            # Your test code that calls eBalance API
            result = submit_report(data)
            
            assert result["success"]
            assert mock_client.call_count("submit_report") == 1
    """
    
    def __init__(self):
        self._responses: dict[str, Any] = {}
        self._calls: dict[str, list] = {}
        self._patch = None
    
    def set_response(self, method: str, response: Any):
        """Set mock response for a method"""
        self._responses[method] = response
    
    def set_error(self, method: str, error: Exception):
        """Set mock error for a method"""
        self._responses[method] = error
    
    def call_count(self, method: str) -> int:
        """Get number of times a method was called"""
        return len(self._calls.get(method, []))
    
    def get_calls(self, method: str) -> list:
        """Get all calls to a method"""
        return self._calls.get(method, [])
    
    def _record_call(self, method: str, *args, **kwargs):
        """Record a method call"""
        if method not in self._calls:
            self._calls[method] = []
        self._calls[method].append({"args": args, "kwargs": kwargs})
    
    def _get_response(self, method: str):
        """Get mock response for method"""
        response = self._responses.get(method)
        if isinstance(response, Exception):
            raise response
        return response or {"success": True}
    
    def __enter__(self):
        # Patch the API client
        self._patch = patch("ebalance.ebalance.api_client.EBalanceClient")
        mock_class = self._patch.start()
        
        # Configure mock instance
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Set up method mocks
        def make_mock_method(method_name):
            def mock_method(*args, **kwargs):
                self._record_call(method_name, *args, **kwargs)
                return self._get_response(method_name)
            return mock_method
        
        for method in ["submit_report", "get_report_status", "get_entity_info", "test_connection"]:
            setattr(mock_instance, method, make_mock_method(method))
        
        return self
    
    def __exit__(self, *args):
        if self._patch:
            self._patch.stop()


# Test data factories

def make_entity_data(
    ent_id: str = "1234567",
    ent_name: str = "Test Company LLC",
    **kwargs
) -> dict:
    """Create test entity data"""
    return {
        "ent_id": ent_id,
        "ent_name": ent_name,
        "state_reg_number": kwargs.get("state_reg_number", "1234567"),
        "address": kwargs.get("address", "Ulaanbaatar, Mongolia"),
        **kwargs
    }


def make_report_data(
    ent_id: str = "1234567",
    year: int = 2024,
    period: int = 1,
    report_type: str = "balance",
    **kwargs
) -> dict:
    """Create test report data"""
    return {
        "ent_id": ent_id,
        "year": year,
        "period": period,
        "report_type": report_type,
        "accounts": kwargs.get("accounts", [
            {"account_code": "1000", "debit": 100000, "credit": 0},
            {"account_code": "2000", "debit": 0, "credit": 100000}
        ]),
        **kwargs
    }


def make_balance_account(
    account_code: str,
    debit: float = 0,
    credit: float = 0,
    **kwargs
) -> dict:
    """Create test balance account entry"""
    return {
        "account_code": account_code,
        "debit": debit,
        "credit": credit,
        **kwargs
    }


# Test fixtures

class TestFixtures:
    """Test fixtures for eBalance"""
    
    @staticmethod
    def create_test_company(name: str = "Test Company") -> str:
        """Create a test company"""
        if frappe.db.exists("Company", name):
            return name
        
        doc = frappe.get_doc({
            "doctype": "Company",
            "company_name": name,
            "abbr": "TC",
            "default_currency": "MNT",
            "country": "Mongolia"
        })
        doc.insert(ignore_permissions=True)
        return str(doc.name) if doc.name else name
    
    @staticmethod
    def create_test_settings(
        enabled: bool = True,
        api_url: str = "https://test.ebalance.gov.mn",
        api_key: str = "test_key_123"
    ) -> None:
        """Create or update test settings"""
        try:
            settings = frappe.get_single("eBalance Settings")
        except frappe.DoesNotExistError:
            settings = frappe.new_doc("eBalance Settings")
        
        setattr(settings, "enabled", enabled)
        setattr(settings, "api_url", api_url)
        setattr(settings, "api_key", api_key)
        settings.save(ignore_permissions=True)
    
    @staticmethod
    def cleanup():
        """Clean up test data"""
        # Clean up test documents
        for doctype in ["eBalance Report Request"]:
            if frappe.db.table_exists(doctype):
                frappe.db.delete(doctype, {"owner": "test@example.com"})
        frappe.db.commit()


# Assertion helpers

def assert_api_called(mock_client: EBalanceMockClient, method: str, times: int = 1):
    """Assert API method was called expected number of times"""
    actual = mock_client.call_count(method)
    assert actual == times, f"Expected {method} to be called {times} times, but was called {actual} times"


def assert_api_called_with(mock_client: EBalanceMockClient, method: str, **expected_kwargs):
    """Assert API method was called with expected arguments"""
    calls = mock_client.get_calls(method)
    assert len(calls) > 0, f"Expected {method} to be called, but it was not"
    
    last_call = calls[-1]
    for key, expected in expected_kwargs.items():
        actual = last_call["kwargs"].get(key)
        assert actual == expected, f"Expected {key}={expected}, but got {key}={actual}"


# Context managers for testing

class DisabledCircuitBreaker:
    """Context manager to disable circuit breaker during tests"""
    
    def __enter__(self):
        self._patch = patch("ebalance.utils.resilience.ebalance_circuit_breaker")
        mock_cb = self._patch.start()
        mock_cb.call.side_effect = lambda func, *args, **kwargs: func(*args, **kwargs)
        return mock_cb
    
    def __exit__(self, *args):
        self._patch.stop()


class MockedSettings:
    """Context manager for mocked settings"""
    
    def __init__(self, **settings):
        self.settings = settings
        self._patch: Any = None
    
    def __enter__(self):
        mock_settings = MagicMock()
        for key, value in self.settings.items():
            setattr(mock_settings, key, value)
        mock_settings.get_password = MagicMock(return_value="test_key")
        
        self._patch = patch("frappe.get_single", return_value=mock_settings)
        self._patch.start()
        return mock_settings
    
    def __exit__(self, *args):
        if self._patch:
            self._patch.stop()
