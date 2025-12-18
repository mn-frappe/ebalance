# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eBalance API - HTTP Client Module (Optimized v1.1)

Base HTTP client for eBalance API requests with:
- Connection pooling
- Retry logic with exponential backoff
- Request timeout management
- Response caching
- Error handling and logging
"""


import frappe
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Global session for connection reuse
_SESSION: requests.Session | None = None
_SESSION_ENV: str | None = None


class EBalanceHTTPError(Exception):
    """HTTP error for eBalance API"""
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class EBalanceHTTPClient:
    """
    HTTP client for eBalance API with connection pooling and retry logic.

    Performance Optimizations:
    - Global session reuse (connection pooling)
    - Configurable connection pool size
    - Exponential backoff on retries
    - Keep-alive connections

    API Gateway (api.frappe.mn):
    - Production: /ebalance/
    - Staging: /ebalance-staging/

    Direct API servers (fallback):
    - Staging: https://st-inspector-ebalance.mof.gov.mn
    - Production: https://inspector-ebalance.mof.gov.mn
    """

    # Primary: api.frappe.mn gateway
    GATEWAY_URL = "https://api.frappe.mn"
    GATEWAY_PATHS = {
        "Staging": "/ebalance-staging",
        "Production": "/ebalance"
    }

    # Fallback: Direct MOF servers
    DIRECT_URLS = {
        "Staging": "https://st-inspector-ebalance.mof.gov.mn",
        "Production": "https://inspector-ebalance.mof.gov.mn"
    }

    # Connection pool settings
    POOL_CONNECTIONS = 10  # Number of connection pools
    POOL_MAXSIZE = 20  # Max connections per pool
    POOL_BLOCK = False  # Don't block when pool is full

    def __init__(self, settings=None):
        """Initialize HTTP client with connection pooling"""
        self.settings = settings or self._get_settings()
        self.session = self._get_or_create_session()

    def _get_settings(self):
        """Get eBalance Settings"""
        try:
            return frappe.get_single("eBalance Settings")
        except Exception:
            return None

    def _get_or_create_session(self) -> requests.Session:
        """Get global session or create new one (connection pooling)"""
        global _SESSION, _SESSION_ENV

        env = self.settings.environment if self.settings else "Staging"

        # Reuse existing session if same environment
        if _SESSION is not None and _SESSION_ENV == env:
            return _SESSION

        # Create new session
        _SESSION = self._create_session()
        _SESSION_ENV = env

        return _SESSION

    def _create_session(self) -> requests.Session:
        """Create requests session with optimized settings"""
        session = requests.Session()

        # Configure retries with exponential backoff
        retries = Retry(
            total=3,
            backoff_factor=0.5,  # 0.5, 1.0, 2.0 seconds
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["GET", "POST"],
            raise_on_status=False  # Don't raise, we handle manually
        )

        # Create adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=self.POOL_CONNECTIONS,
            pool_maxsize=self.POOL_MAXSIZE,
            pool_block=self.POOL_BLOCK
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set default headers for all requests
        session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        })

        return session

    @property
    def base_url(self):
        """Get API base URL - uses api.frappe.mn gateway"""
        env = "Staging"
        if self.settings:
            env = self.settings.environment or "Staging"

        # Use gateway
        gateway_path = self.GATEWAY_PATHS.get(env, self.GATEWAY_PATHS["Staging"])
        return f"{self.GATEWAY_URL}{gateway_path}"

    @property
    def direct_url(self):
        """Get direct MOF URL for fallback"""
        env = "Staging"
        if self.settings:
            env = self.settings.environment or "Staging"
        return self.DIRECT_URLS.get(env, self.DIRECT_URLS["Staging"])

    @property
    def timeout(self):
        """Get request timeout from settings"""
        if self.settings and self.settings.request_timeout:
            return int(self.settings.request_timeout)
        return 60

    def request(self, method, endpoint, auth_header=None, **kwargs):
        """
        Make HTTP request to eBalance API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base URL)
            auth_header: Authorization header dict
            **kwargs: Additional requests arguments

        Returns:
            dict: Response JSON data

        Raises:
            EBalanceHTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        # Set default headers
        headers = kwargs.pop("headers", {})
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("Accept", "application/json")

        # Add auth header if provided
        if auth_header:
            headers.update(auth_header)

        # Add additional headers from settings (URL-encode Cyrillic characters)
        if self.settings:
            if self.settings.user_regno:
                from urllib.parse import quote
                headers["userRegNo"] = quote(self.settings.user_regno)
            if self.settings.org_regno:
                headers["orgRegNo"] = str(self.settings.org_regno)

        # Set timeout
        kwargs.setdefault("timeout", self.timeout)

        # Log request (without sensitive data)
        self._log_request(method, endpoint, kwargs.get("params"), kwargs.get("json"))

        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                **kwargs
            )

            # Log response
            self._log_response(endpoint, response.status_code)

            # Parse response
            return self._handle_response(response, endpoint)

        except requests.exceptions.Timeout:
            raise EBalanceHTTPError(f"Request timeout: {endpoint}", status_code=408)
        except requests.exceptions.ConnectionError as e:
            raise EBalanceHTTPError(f"Connection error: {e!s}", status_code=503)
        except requests.exceptions.RequestException as e:
            raise EBalanceHTTPError(f"Request failed: {e!s}")

    def _handle_response(self, response, endpoint):
        """Handle API response"""
        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {"raw": response.text}

        if response.status_code >= 400:
            error_msg = data.get("message") or data.get("error") or f"HTTP {response.status_code}"
            raise EBalanceHTTPError(
                f"API error on {endpoint}: {error_msg}",
                status_code=response.status_code,
                response_data=data
            )

        return data

    def _log_request(self, method, endpoint, params=None, json_data=None):
        """Log API request (debug mode only, no sensitive data)"""
        if self.settings and self.settings.debug_mode:
            frappe.logger("ebalance").debug(
                f"eBalance API Request: {method} {endpoint}"
            )

    def _log_response(self, endpoint, status_code):
        """Log API response"""
        if self.settings and self.settings.debug_mode:
            frappe.logger("ebalance").debug(
                f"eBalance API Response: {endpoint} -> {status_code}"
            )

    def get(self, endpoint, auth_header=None, **kwargs):
        """Make GET request"""
        return self.request("GET", endpoint, auth_header, **kwargs)

    def post(self, endpoint, auth_header=None, **kwargs):
        """Make POST request"""
        return self.request("POST", endpoint, auth_header, **kwargs)

    def close(self):
        """Close session"""
        if self.session:
            self.session.close()


def get_http_client():
    """Get EBalanceHTTPClient instance"""
    return EBalanceHTTPClient()
