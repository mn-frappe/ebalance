# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Tests for eBalance Validators

Tests the validation utilities for API payload validation.
"""

import unittest
from datetime import date, datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from ebalance.utils.validators import (
    ValidationError,
    ValidationResult,
    Validator,
    validate_balance_data,
    validate_entity_id,
    validate_report_period,
    validate_report_request,
)


class TestValidationError(unittest.TestCase):
    """Test ValidationError dataclass"""

    def test_validation_error_creation(self):
        """Test creating a validation error"""
        error = ValidationError(
            field="test_field",
            message="Test message",
            code="test_code",
            value="test_value"
        )
        self.assertEqual(error.field, "test_field")
        self.assertEqual(error.message, "Test message")
        self.assertEqual(error.code, "test_code")
        self.assertEqual(error.value, "test_value")

    def test_validation_error_defaults(self):
        """Test validation error default values"""
        error = ValidationError(field="test", message="msg")
        self.assertEqual(error.code, "invalid")
        self.assertIsNone(error.value)


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass"""

    def test_valid_result(self):
        """Test valid result creation"""
        result = ValidationResult(is_valid=True, errors=[])
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])

    def test_invalid_result(self):
        """Test invalid result creation"""
        errors = [ValidationError(field="test", message="error")]
        result = ValidationResult(is_valid=False, errors=errors)
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)


class TestValidator(unittest.TestCase):
    """Test Validator class"""

    def test_required_with_value(self):
        """Test required validation with value"""
        result = Validator().field("name", "John").required().validate()
        self.assertTrue(result.is_valid)

    def test_required_with_none(self):
        """Test required validation with None"""
        result = Validator().field("name", None).required().validate()
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].code, "required")

    def test_required_with_empty_string(self):
        """Test required validation with empty string"""
        result = Validator().field("name", "").required().validate()
        self.assertFalse(result.is_valid)

    def test_optional_with_none(self):
        """Test optional skips remaining validations when None"""
        result = (Validator()
            .field("email", None)
            .optional()
            .regex(r"^\S+@\S+$")
            .validate())
        self.assertTrue(result.is_valid)

    def test_optional_with_value(self):
        """Test optional continues validation when value present"""
        result = (Validator()
            .field("email", "invalid")
            .optional()
            .regex(r"^\S+@\S+$")
            .validate())
        self.assertFalse(result.is_valid)

    def test_min_length(self):
        """Test minimum length validation"""
        result = Validator().field("code", "AB").min_length(3).validate()
        self.assertFalse(result.is_valid)
        
        result = Validator().field("code", "ABC").min_length(3).validate()
        self.assertTrue(result.is_valid)

    def test_max_length(self):
        """Test maximum length validation"""
        result = Validator().field("code", "ABCDEF").max_length(5).validate()
        self.assertFalse(result.is_valid)
        
        result = Validator().field("code", "ABC").max_length(5).validate()
        self.assertTrue(result.is_valid)

    def test_regex(self):
        """Test regex validation"""
        result = Validator().field("id", "1234567").regex(r"^\d{7}$").validate()
        self.assertTrue(result.is_valid)
        
        result = Validator().field("id", "123").regex(r"^\d{7}$").validate()
        self.assertFalse(result.is_valid)

    def test_between(self):
        """Test between range validation"""
        result = Validator().field("year", 2024).between(2000, 2100).validate()
        self.assertTrue(result.is_valid)
        
        result = Validator().field("year", 1999).between(2000, 2100).validate()
        self.assertFalse(result.is_valid)
        
        result = Validator().field("year", 2101).between(2000, 2100).validate()
        self.assertFalse(result.is_valid)

    def test_in_list(self):
        """Test in_list validation"""
        result = Validator().field("status", "active").in_list(["active", "inactive"]).validate()
        self.assertTrue(result.is_valid)
        
        result = Validator().field("status", "unknown").in_list(["active", "inactive"]).validate()
        self.assertFalse(result.is_valid)

    def test_is_date_with_date_object(self):
        """Test is_date with date object"""
        result = Validator().field("date", date.today()).is_date().validate()
        self.assertTrue(result.is_valid)

    def test_is_date_with_datetime_object(self):
        """Test is_date with datetime object"""
        result = Validator().field("date", datetime.now()).is_date().validate()
        self.assertTrue(result.is_valid)

    def test_is_date_with_valid_string(self):
        """Test is_date with valid date string"""
        result = Validator().field("date", "2024-12-19").is_date().validate()
        self.assertTrue(result.is_valid)

    def test_is_date_with_invalid_string(self):
        """Test is_date with invalid date string"""
        result = Validator().field("date", "not-a-date").is_date().validate()
        self.assertFalse(result.is_valid)

    def test_custom_validator(self):
        """Test custom validation function"""
        is_even = lambda x: x % 2 == 0
        
        result = Validator().field("num", 4).custom(is_even, "Must be even").validate()
        self.assertTrue(result.is_valid)
        
        result = Validator().field("num", 5).custom(is_even, "Must be even").validate()
        self.assertFalse(result.is_valid)

    def test_chained_validations(self):
        """Test multiple chained validations"""
        result = (Validator()
            .field("entity_id", "1234567")
            .required()
            .min_length(7)
            .max_length(7)
            .regex(r"^\d+$")
            .validate())
        self.assertTrue(result.is_valid)

    def test_multiple_fields(self):
        """Test validating multiple fields"""
        result = (Validator()
            .field("name", "John")
            .required()
            .min_length(2)
            .field("age", 25)
            .required()
            .between(1, 150)
            .field("email", "john@test.com")
            .required()
            .validate())
        self.assertTrue(result.is_valid)

    def test_multiple_fields_with_errors(self):
        """Test multiple fields with multiple errors"""
        result = (Validator()
            .field("name", "")
            .required()
            .field("age", 200)
            .between(1, 150)
            .validate())
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 2)


class TestEntityIdValidation(unittest.TestCase):
    """Test entity ID validation"""

    def test_valid_entity_id(self):
        """Test valid 7-digit entity ID"""
        result = validate_entity_id("1234567")
        self.assertTrue(result.is_valid)

    def test_invalid_entity_id_too_short(self):
        """Test entity ID too short"""
        result = validate_entity_id("123456")
        self.assertFalse(result.is_valid)

    def test_invalid_entity_id_too_long(self):
        """Test entity ID too long"""
        result = validate_entity_id("12345678")
        self.assertFalse(result.is_valid)

    def test_invalid_entity_id_with_letters(self):
        """Test entity ID with letters"""
        result = validate_entity_id("123456A")
        self.assertFalse(result.is_valid)

    def test_invalid_entity_id_empty(self):
        """Test empty entity ID"""
        result = validate_entity_id("")
        self.assertFalse(result.is_valid)


class TestReportPeriodValidation(unittest.TestCase):
    """Test report period validation"""

    def test_valid_annual_report(self):
        """Test valid annual report (period=0)"""
        result = validate_report_period(2024, 0)
        self.assertTrue(result.is_valid)

    def test_valid_monthly_report(self):
        """Test valid monthly report"""
        for month in range(1, 13):
            result = validate_report_period(2024, month)
            self.assertTrue(result.is_valid, f"Month {month} should be valid")

    def test_invalid_period(self):
        """Test invalid period"""
        result = validate_report_period(2024, 13)
        self.assertFalse(result.is_valid)

    def test_invalid_year_too_old(self):
        """Test year too old"""
        result = validate_report_period(1999, 1)
        self.assertFalse(result.is_valid)


class TestReportRequestValidation(unittest.TestCase):
    """Test report request validation"""

    def test_valid_report_request(self):
        """Test valid report request"""
        data = {
            "ent_id": "1234567",
            "year": 2024,
            "period": 0,
            "report_type": "balance"
        }
        result = validate_report_request(data)
        self.assertTrue(result.is_valid)

    def test_invalid_report_request_missing_fields(self):
        """Test report request with missing fields"""
        data = {
            "ent_id": "1234567"
        }
        result = validate_report_request(data)
        self.assertFalse(result.is_valid)
        self.assertGreaterEqual(len(result.errors), 3)

    def test_invalid_report_request_invalid_entity(self):
        """Test report request with invalid entity ID"""
        data = {
            "ent_id": "123",
            "year": 2024,
            "period": 0,
            "report_type": "balance"
        }
        result = validate_report_request(data)
        self.assertFalse(result.is_valid)


class TestBalanceDataValidation(unittest.TestCase):
    """Test balance data validation"""

    def test_valid_balance_data(self):
        """Test valid balance data"""
        data = {
            "accounts": [
                {"account_code": "1000", "debit": 1000.00, "credit": 0},
                {"account_code": "2000", "debit": 0, "credit": 1000.00}
            ]
        }
        result = validate_balance_data(data)
        self.assertTrue(result.is_valid)

    def test_invalid_balance_data_missing_accounts(self):
        """Test balance data without accounts"""
        data = {}
        result = validate_balance_data(data)
        self.assertFalse(result.is_valid)

    def test_invalid_balance_data_missing_account_code(self):
        """Test balance data with missing account code"""
        data = {
            "accounts": [
                {"debit": 1000.00, "credit": 0}
            ]
        }
        result = validate_balance_data(data)
        self.assertFalse(result.is_valid)
