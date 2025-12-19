# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Validation Utilities for eBalance

Provides data validation for API payloads before sending to MOF.
Catches errors early before API submission.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable

import frappe
from frappe import _


@dataclass
class ValidationError:
    """Single validation error"""
    field: str
    message: str
    code: str = "invalid"
    value: Any = None


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: list[ValidationError]
    
    def raise_if_invalid(self):
        """Raise ValidationException if invalid"""
        if not self.is_valid:
            error_messages = [f"{e.field}: {e.message}" for e in self.errors]
            frappe.throw(
                _("Validation failed: {0}").format("; ".join(error_messages)),
                title=_("eBalance Validation Error")
            )


class Validator:
    """
    Chainable field validator.
    
    Usage:
        validator = Validator()
        result = (validator
            .field("ent_id", entity_id)
            .required()
            .regex(r"^\\d{7}$", "Must be 7-digit number")
            .field("year", year)
            .required()
            .between(2000, 2100)
            .validate())
        
        result.raise_if_invalid()
    """
    
    def __init__(self):
        self._errors: list[ValidationError] = []
        self._current_field: str | None = None
        self._current_value: Any = None
        self._skip_remaining = False
    
    def field(self, name: str, value: Any) -> "Validator":
        """Start validating a new field"""
        self._current_field = name
        self._current_value = value
        self._skip_remaining = False
        return self
    
    def _add_error(self, message: str, code: str = "invalid"):
        """Add validation error for current field"""
        self._errors.append(ValidationError(
            field=self._current_field or "unknown",
            message=message,
            code=code,
            value=self._current_value
        ))
    
    def required(self, message: str | None = None) -> "Validator":
        """Value must not be None or empty"""
        if self._skip_remaining:
            return self
        
        if self._current_value is None or self._current_value == "":
            self._add_error(message or _("This field is required"), "required")
            self._skip_remaining = True
        return self
    
    def optional(self) -> "Validator":
        """Skip remaining validations if value is None/empty"""
        if self._current_value is None or self._current_value == "":
            self._skip_remaining = True
        return self
    
    def regex(self, pattern: str, message: str | None = None) -> "Validator":
        """Value must match regex pattern"""
        if self._skip_remaining:
            return self
        
        if not re.match(pattern, str(self._current_value)):
            self._add_error(message or _("Invalid format"), "format")
        return self
    
    def min_length(self, length: int, message: str | None = None) -> "Validator":
        """String must have minimum length"""
        if self._skip_remaining:
            return self
        
        if len(str(self._current_value)) < length:
            self._add_error(message or _("Must be at least {0} characters").format(length), "min_length")
        return self
    
    def max_length(self, length: int, message: str | None = None) -> "Validator":
        """String must have maximum length"""
        if self._skip_remaining:
            return self
        
        if len(str(self._current_value)) > length:
            self._add_error(message or _("Must be at most {0} characters").format(length), "max_length")
        return self
    
    def between(self, min_val: float, max_val: float, message: str | None = None) -> "Validator":
        """Numeric value must be within range"""
        if self._skip_remaining:
            return self
        
        try:
            val = float(self._current_value)
            if val < min_val or val > max_val:
                self._add_error(message or _("Must be between {0} and {1}").format(min_val, max_val), "range")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def positive(self, message: str | None = None) -> "Validator":
        """Numeric value must be positive"""
        if self._skip_remaining:
            return self
        
        try:
            if float(self._current_value) <= 0:
                self._add_error(message or _("Must be positive"), "positive")
        except (ValueError, TypeError):
            self._add_error(_("Must be a number"), "type")
        return self
    
    def in_list(self, valid_values: list, message: str | None = None) -> "Validator":
        """Value must be in list of valid values"""
        if self._skip_remaining:
            return self
        
        if self._current_value not in valid_values:
            self._add_error(
                message or _("Must be one of: {0}").format(", ".join(str(v) for v in valid_values)),
                "choices"
            )
        return self
    
    def is_date(self, message: str | None = None) -> "Validator":
        """Value must be a valid date"""
        if self._skip_remaining:
            return self
        
        if isinstance(self._current_value, (date, datetime)):
            return self
        
        try:
            if isinstance(self._current_value, str):
                datetime.strptime(self._current_value, "%Y-%m-%d")
        except ValueError:
            self._add_error(message or _("Must be a valid date (YYYY-MM-DD)"), "date")
        return self
    
    def custom(self, validator_func: Callable[[Any], bool], message: str) -> "Validator":
        """Custom validation function"""
        if self._skip_remaining:
            return self
        
        if not validator_func(self._current_value):
            self._add_error(message, "custom")
        return self
    
    def validate(self) -> ValidationResult:
        """Return validation result"""
        return ValidationResult(
            is_valid=len(self._errors) == 0,
            errors=self._errors.copy()
        )


# eBalance-specific validators

def validate_entity_id(entity_id: str) -> ValidationResult:
    """Validate Mongolian entity registration number"""
    return (Validator()
        .field("ent_id", entity_id)
        .required()
        .regex(r"^\d{7}$", _("Entity ID must be exactly 7 digits"))
        .validate())


def validate_report_period(year: int, period: int) -> ValidationResult:
    """Validate report year and period"""
    current_year = datetime.now().year
    
    return (Validator()
        .field("year", year)
        .required()
        .between(2000, current_year + 1, _("Invalid report year"))
        .field("period", period)
        .required()
        .in_list(list(range(0, 13)), _("Period must be 0 (annual) or 1-12 (monthly)"))
        .validate())


def validate_report_request(data: dict) -> ValidationResult:
    """Validate eBalance report request data"""
    v = Validator()
    
    # Required fields
    v.field("ent_id", data.get("ent_id")).required().regex(r"^\d{7}$")
    v.field("year", data.get("year")).required().between(2000, datetime.now().year + 1)
    v.field("period", data.get("period")).required().in_list(list(range(0, 13)))
    v.field("report_type", data.get("report_type")).required()
    
    # Optional fields with validation
    v.field("certificate_number", data.get("certificate_number")).optional().max_length(50)
    
    return v.validate()


def validate_balance_data(data: dict) -> ValidationResult:
    """Validate balance report data structure"""
    v = Validator()
    
    v.field("accounts", data.get("accounts")).required()
    
    if isinstance(data.get("accounts"), list):
        for i, account in enumerate(data["accounts"]):
            v.field(f"accounts[{i}].account_code", account.get("account_code")).required()
            v.field(f"accounts[{i}].debit", account.get("debit", 0)).optional().custom(
                lambda x: float(x) >= 0, _("Debit must be non-negative")
            )
            v.field(f"accounts[{i}].credit", account.get("credit", 0)).optional().custom(
                lambda x: float(x) >= 0, _("Credit must be non-negative")
            )
    
    return v.validate()


# Helper function

def validate_or_throw(result: ValidationResult):
    """Raise exception if validation failed"""
    result.raise_if_invalid()
