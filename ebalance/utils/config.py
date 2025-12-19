# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Configuration Validation for eBalance

Validates required settings on startup and provides configuration helpers.
"""

from dataclasses import dataclass
from typing import Any

import frappe
from frappe import _


@dataclass
class ConfigIssue:
    """Configuration issue"""
    field: str
    message: str
    severity: str = "error"  # error, warning, info


@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    issues: list[ConfigIssue]
    
    def get_errors(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "error"]
    
    def get_warnings(self) -> list[ConfigIssue]:
        return [i for i in self.issues if i.severity == "warning"]


class ConfigValidator:
    """
    Validates eBalance configuration.
    
    Usage:
        validator = ConfigValidator()
        result = validator.validate()
        
        if not result.is_valid:
            for issue in result.get_errors():
                print(f"{issue.field}: {issue.message}")
    """
    
    SETTINGS_DOCTYPE = "eBalance Settings"
    
    def validate(self) -> ConfigValidationResult:
        """Validate all configuration"""
        issues: list[ConfigIssue] = []
        
        # Check settings doctype exists
        if not self._settings_exist():
            issues.append(ConfigIssue(
                field="settings",
                message=_("eBalance Settings not found. Please configure the app."),
                severity="error"
            ))
            return ConfigValidationResult(is_valid=False, issues=issues)
        
        settings = frappe.get_single(self.SETTINGS_DOCTYPE)
        
        # Validate API configuration
        issues.extend(self._validate_api_config(settings))
        
        # Validate authentication
        issues.extend(self._validate_auth_config(settings))
        
        # Validate company mapping
        issues.extend(self._validate_company_config(settings))
        
        # Check environment
        issues.extend(self._validate_environment())
        
        is_valid = len([i for i in issues if i.severity == "error"]) == 0
        return ConfigValidationResult(is_valid=is_valid, issues=issues)
    
    def _settings_exist(self) -> bool:
        """Check if settings doctype exists and has records"""
        try:
            frappe.get_single(self.SETTINGS_DOCTYPE)
            return True
        except Exception:
            return False
    
    def _validate_api_config(self, settings) -> list[ConfigIssue]:
        """Validate API configuration"""
        issues = []
        
        if not settings.enabled:
            issues.append(ConfigIssue(
                field="enabled",
                message=_("eBalance integration is disabled"),
                severity="info"
            ))
            return issues
        
        if not settings.api_url:
            issues.append(ConfigIssue(
                field="api_url",
                message=_("API URL is required"),
                severity="error"
            ))
        elif not settings.api_url.startswith("https://"):
            issues.append(ConfigIssue(
                field="api_url",
                message=_("API URL should use HTTPS for security"),
                severity="warning"
            ))
        
        return issues
    
    def _validate_auth_config(self, settings) -> list[ConfigIssue]:
        """Validate authentication configuration"""
        issues = []
        
        if not settings.enabled:
            return issues
        
        if not settings.get_password("api_key"):
            issues.append(ConfigIssue(
                field="api_key",
                message=_("API key is required for authentication"),
                severity="error"
            ))
        
        # Check certificate if required
        if hasattr(settings, "use_certificate") and settings.use_certificate:
            if not settings.certificate:
                issues.append(ConfigIssue(
                    field="certificate",
                    message=_("Certificate is required when certificate auth is enabled"),
                    severity="error"
                ))
        
        return issues
    
    def _validate_company_config(self, settings) -> list[ConfigIssue]:
        """Validate company/entity configuration"""
        issues = []
        
        if not settings.enabled:
            return issues
        
        # Check if company mapping exists
        if hasattr(settings, "company_mappings"):
            if not settings.company_mappings or len(settings.company_mappings) == 0:
                issues.append(ConfigIssue(
                    field="company_mappings",
                    message=_("No company to entity mappings configured"),
                    severity="warning"
                ))
        
        return issues
    
    def _validate_environment(self) -> list[ConfigIssue]:
        """Validate environment setup"""
        issues = []
        
        # Check Redis connectivity
        try:
            frappe.cache().set_value("ebalance:config_test", "ok", expires_in_sec=5)
            frappe.cache().delete_value("ebalance:config_test")
        except Exception as e:
            issues.append(ConfigIssue(
                field="redis",
                message=_("Redis connectivity issue: {0}").format(str(e)),
                severity="warning"
            ))
        
        return issues


def validate_config() -> ConfigValidationResult:
    """Validate eBalance configuration"""
    return ConfigValidator().validate()


def validate_config_on_startup():
    """
    Validate configuration on app startup.
    
    Add to hooks.py:
        on_login = [
            "ebalance.utils.config.validate_config_on_startup"
        ]
    
    Or for boot:
        boot_session = [
            "ebalance.utils.config.validate_config_on_startup"
        ]
    """
    try:
        result = validate_config()
        
        if not result.is_valid:
            for issue in result.get_errors():
                frappe.logger("ebalance").error(
                    f"Config error - {issue.field}: {issue.message}"
                )
        
        for issue in result.get_warnings():
            frappe.logger("ebalance").warning(
                f"Config warning - {issue.field}: {issue.message}"
            )
    except Exception as e:
        frappe.logger("ebalance").error(f"Config validation failed: {e}")


def get_config_status() -> dict:
    """Get configuration status for health checks"""
    result = validate_config()
    
    return {
        "valid": result.is_valid,
        "errors": [{"field": i.field, "message": i.message} for i in result.get_errors()],
        "warnings": [{"field": i.field, "message": i.message} for i in result.get_warnings()]
    }


# API endpoint
@frappe.whitelist()
def check_configuration():
    """Check eBalance configuration status"""
    frappe.only_for(["System Manager", "Administrator"])
    return get_config_status()
