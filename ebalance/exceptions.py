# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
"""
eBalance Exception Hierarchy

Provides a consistent exception hierarchy for eBalance operations.
All custom exceptions inherit from EBalanceError for easy catching.
"""

from __future__ import annotations

from typing import Any


class EBalanceError(Exception):
    """Base exception for all eBalance errors.
    
    All eBalance-specific exceptions should inherit from this class.
    This allows catching all eBalance errors with a single except clause.
    
    Example:
        try:
            submit_report(data)
        except EBalanceError as e:
            handle_ebalance_error(e)
    """
    
    def __init__(self, message: str, code: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details
        }


class EBalanceAPIError(EBalanceError):
    """Error from eBalance API response.
    
    Raised when the eBalance API returns an error response.
    
    Attributes:
        status_code: HTTP status code
        response_data: Raw response data from API
    """
    
    def __init__(
        self,
        message: str,
        code: str | None = None,
        status_code: int | None = None,
        response_data: Any = None
    ):
        super().__init__(message, code)
        self.status_code = status_code
        self.response_data = response_data


class EBalanceConnectionError(EBalanceError):
    """Network/connection error to eBalance API.
    
    Raised when unable to connect to the eBalance API server.
    """
    pass


class EBalanceAuthError(EBalanceError):
    """Authentication error with eBalance API.
    
    Raised when API credentials are invalid or token has expired.
    """
    pass


class EBalanceValidationError(EBalanceError):
    """Validation error for eBalance data.
    
    Raised when input data fails validation before API call.
    
    Attributes:
        field: Field that failed validation
        errors: List of validation errors
    """
    
    def __init__(
        self,
        message: str,
        field: str | None = None,
        errors: list[str] | None = None
    ):
        super().__init__(message, code="VALIDATION_ERROR")
        self.field = field
        self.errors = errors or []


class EBalanceReportError(EBalanceError):
    """Error during report operations.
    
    Raised when report submission or query fails.
    """
    pass


class EBalanceConfigError(EBalanceError):
    """Configuration error for eBalance.
    
    Raised when required settings are missing or invalid.
    """
    pass


class EBalanceTimeoutError(EBalanceError):
    """Timeout error for eBalance API call.
    
    Raised when API request exceeds timeout limit.
    """
    pass


class EBalanceRateLimitError(EBalanceError):
    """Rate limit exceeded for eBalance API.
    
    Raised when too many requests are made in a short period.
    
    Attributes:
        retry_after: Seconds to wait before retrying
    """
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, code="RATE_LIMIT")
        self.retry_after = retry_after


# Export all exceptions
__all__ = [
    "EBalanceError",
    "EBalanceAPIError",
    "EBalanceConnectionError",
    "EBalanceAuthError",
    "EBalanceValidationError",
    "EBalanceReportError",
    "EBalanceConfigError",
    "EBalanceTimeoutError",
    "EBalanceRateLimitError",
]
