# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false

"""
eBalance API - Authentication Module

Handles ITC OAuth2 authentication for eBalance API.
Same auth server as eBarimt (auth.itc.gov.mn)
"""

import frappe
import requests
from datetime import datetime, timedelta


class EBalanceAuthError(Exception):
	"""Authentication error for eBalance API"""
	pass


class EBalanceAuth:
	"""
	ITC OAuth2 Authentication handler for eBalance.
	
	Auth Gateway (api.frappe.mn):
	- Production: /auth/itc/
	- Staging: /auth/itc-staging/
	
	Direct Auth servers (fallback):
	- Staging: https://st.auth.itc.gov.mn/auth/realms/Staging
	- Production: https://auth.itc.gov.mn/auth/realms/ITC
	"""
	
	# Primary: api.frappe.mn gateway
	GATEWAY_URL = "https://api.frappe.mn"
	GATEWAY_PATHS = {
		"Staging": "/auth/itc-staging",
		"Production": "/auth/itc"
	}
	
	# Fallback: Direct auth servers
	AUTH_URLS = {
		"Staging": "https://st.auth.itc.gov.mn/auth/realms/Staging",
		"Production": "https://auth.itc.gov.mn/auth/realms/ITC"
	}
	
	# Fixed OAuth2 parameters
	GRANT_TYPE = "password"
	CLIENT_ID = "vatps"  # Same as eBarimt
	
	def __init__(self, settings=None):
		"""
		Initialize auth handler.
		
		Args:
			settings: eBalance Settings doc or None to fetch automatically
		"""
		self.settings = settings or self._get_settings()
		self._token = None
		self._token_expiry = None
	
	def _get_settings(self):
		"""Get eBalance Settings singleton"""
		try:
			return frappe.get_single("eBalance Settings")
		except Exception as e:
			frappe.throw(
				"eBalance Settings not configured. Please configure in MN Settings > eBalance.",
				title="eBalance Configuration Required"
			)
	
	@property
	def auth_url(self):
		"""Get auth URL - uses api.frappe.mn gateway"""
		env = self.settings.environment or "Staging"
		gateway_path = self.GATEWAY_PATHS.get(env, self.GATEWAY_PATHS["Staging"])
		return f"{self.GATEWAY_URL}{gateway_path}"
	
	@property
	def auth_url_direct(self):
		"""Get direct auth URL for fallback"""
		env = self.settings.environment or "Staging"
		return self.AUTH_URLS.get(env, self.AUTH_URLS["Staging"])
	
	@property
	def token_endpoint(self):
		"""Get OAuth2 token endpoint"""
		return f"{self.auth_url}/protocol/openid-connect/token"
	
	def get_token(self, force_refresh=False):
		"""
		Get valid access token, refreshing if necessary.
		
		Args:
			force_refresh: Force token refresh even if cached
			
		Returns:
			str: Valid access token
			
		Raises:
			EBalanceAuthError: If authentication fails
		"""
		# Check cached token
		if not force_refresh and self._is_token_valid():
			return self._token
		
		# Check stored token in settings
		if not force_refresh and self._load_stored_token():
			return self._token
		
		# Request new token
		return self._request_new_token()
	
	def _is_token_valid(self):
		"""Check if cached token is still valid"""
		if not self._token or not self._token_expiry:
			return False
		# Add 60 second buffer
		return datetime.now() < (self._token_expiry - timedelta(seconds=60))
	
	def _load_stored_token(self):
		"""Load token from settings if still valid"""
		try:
			stored_token = self.settings.get_password("access_token")
			stored_expiry = self.settings.token_expiry
			
			if stored_token and stored_expiry:
				expiry_dt = frappe.utils.get_datetime(stored_expiry)
				if datetime.now() < (expiry_dt - timedelta(seconds=60)):
					self._token = stored_token
					self._token_expiry = expiry_dt
					return True
		except Exception:
			pass
		return False
	
	def _request_new_token(self):
		"""
		Request new token from ITC OAuth2 server.
		
		SECURITY: Password is decrypted only for this request,
		never logged or stored in plain text.
		"""
		try:
			# Get credentials (password is decrypted here)
			username = self.settings.username
			password = self.settings.get_password("password")
			
			if not username or not password:
				raise EBalanceAuthError("Username or password not configured")
			
			# Make token request
			response = requests.post(
				self.token_endpoint,
				data={
					"grant_type": self.GRANT_TYPE,
					"client_id": self.CLIENT_ID,
					"username": username,
					"password": password  # Decrypted, used only here
				},
				headers={
					"Content-Type": "application/x-www-form-urlencoded"
				},
				timeout=30
			)
			
			if response.status_code == 200:
				data = response.json()
				self._token = data.get("access_token")
				expires_in = data.get("expires_in", 3600)
				self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
				
				# Store token in settings (encrypted)
				self._store_token()
				
				return self._token
			elif response.status_code == 401:
				raise EBalanceAuthError("Invalid username or password")
			else:
				raise EBalanceAuthError(f"Auth server error: {response.status_code}")
				
		except requests.exceptions.Timeout:
			raise EBalanceAuthError("Auth server timeout")
		except requests.exceptions.RequestException as e:
			raise EBalanceAuthError(f"Network error: {str(e)}")
	
	def _store_token(self):
		"""Store token in settings (encrypted)"""
		try:
			# Use frappe.db directly to avoid triggering hooks
			frappe.db.set_value(
				"eBalance Settings",
				"eBalance Settings",
				{
					"access_token": self._token,
					"token_expiry": self._token_expiry
				},
				update_modified=False
			)
			frappe.db.commit()
		except Exception:
			# Non-critical, token still works in memory
			pass
	
	def revoke_token(self):
		"""Revoke/logout current token"""
		try:
			if self._token:
				logout_url = f"{self.auth_url}/protocol/openid-connect/logout"
				requests.post(
					logout_url,
					headers={"Authorization": f"Bearer {self._token}"},
					timeout=10
				)
		except Exception:
			pass
		finally:
			self._token = None
			self._token_expiry = None
			# Clear stored token
			try:
				frappe.db.set_value(
					"eBalance Settings",
					"eBalance Settings",
					{"access_token": "", "token_expiry": None},
					update_modified=False
				)
				frappe.db.commit()
			except Exception:
				pass
	
	def get_auth_header(self):
		"""Get Authorization header for API requests"""
		token = self.get_token()
		return {"Authorization": f"Bearer {token}"}


def get_auth():
	"""Get EBalanceAuth instance"""
	return EBalanceAuth()
