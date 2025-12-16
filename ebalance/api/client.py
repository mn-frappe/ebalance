# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false

"""
eBalance API Client

Full implementation of eBalance API (10 endpoints):
1. getWritingConfigs - Report periods list
2. getUserRoles - User permissions
3. getAllConfigWithReportOrgList - Connected periods
4. getReportUserOrgHdrList - Report requests
5. decideReportUserOrgHdr - Begin report entry
6. getReportData - Form data & validation
7. getReportPackageMap - Form names
8. saveReportData - Save draft
9. sendReportData - Submit final
10. getConfirmedReportData - Query confirmed reports
"""

import frappe
from ebalance.api.auth import EBalanceAuth, EBalanceAuthError
from ebalance.api.http_client import EBalanceHTTPClient, EBalanceHTTPError


class EBalanceClient:
	"""
	eBalance API Client for Ministry of Finance Financial Reporting System.
	
	Usage:
		client = EBalanceClient()
		
		# Get available report periods
		periods = client.get_writing_configs()
		
		# Get user roles
		roles = client.get_user_roles()
		
		# Submit financial report
		result = client.send_report(report_user_org_hdr_id)
	"""
	
	# API endpoint paths
	ENDPOINTS = {
		"writing_configs": "/rest/mof-ebalance-inspector-service/tpiRequest/getWritingConfigs",
		"user_roles": "/rest/mof-ebalance-out-service/perRole/getUserRoles",
		"report_org_list": "/rest/mof-ebalance-out-service/reportConnectConfig/getAllConfigWithReportOrgList",
		"report_requests": "/rest/mof-ebalance-out-service/reportConnectConfig/getReportUserOrgHdrList",
		"decide_report": "/rest/mof-ebalance-out-service/reportConnectConfig/decideReportUserOrgHdr",
		"report_data": "/rest/mof-ebalance-out-service/reportData/getReportData",
		"report_package_map": "/rest/mof-ebalance-out-service/reportConnectConfig/getReportPackageMap",
		"save_report": "/rest/mof-ebalance-out-service/calculate/saveReportData",
		"send_report": "/rest/mof-ebalance-out-service/calculate/sendReportData",
		"confirmed_report": "/rest/tpiRequest/getConfirmedReportData"
	}
	
	def __init__(self, settings=None):
		"""
		Initialize eBalance client.
		
		Args:
			settings: eBalance Settings doc or None
		"""
		self.settings = settings or self._get_settings()
		self.auth = EBalanceAuth(self.settings)
		self.http = EBalanceHTTPClient(self.settings)
	
	def _get_settings(self):
		"""Get eBalance Settings singleton"""
		return frappe.get_single("eBalance Settings")
	
	def _get_auth_header(self):
		"""Get authorization header"""
		return self.auth.get_auth_header()
	
	def _get_common_headers(self, **extra_headers):
		"""Get common request headers"""
		headers = {
			"userRegNo": self.settings.user_regno or self.settings.username,
			"orgRegNo": self.settings.org_regno
		}
		headers.update(extra_headers)
		return headers
	
	# =========================================================================
	# API 1: Get Writing Configs (Report Periods)
	# =========================================================================
	
	def get_writing_configs(self):
		"""
		Get available report periods (тайлант үеийн жагсаалт).
		
		Returns:
			list: List of report periods with code and name
			
		Example response:
			[
				{"code": "End_2024_H_2", "name": "2024 оны жилийн эцсийн тайлан"},
				{"code": "SubEnd_2024_M_1", "name": "2024 оны хагас жилийн тайлан"}
			]
		"""
		response = self.http.get(
			self.ENDPOINTS["writing_configs"],
			auth_header=self._get_auth_header()
		)
		
		if response.get("statusCode") == 200:
			return response.get("result", [])
		
		raise EBalanceHTTPError(
			response.get("message", "Failed to get writing configs"),
			status_code=response.get("statusCode")
		)
	
	# =========================================================================
	# API 2: Get User Roles
	# =========================================================================
	
	def get_user_roles(self):
		"""
		Get user's role and organization info.
		
		Returns the perMapUserRoleId needed for other API calls.
		
		Returns:
			dict: User role info including:
				- id (perMapUserRoleId)
				- perRole (role name/description)
				- userOrganization (regNo, name)
		"""
		headers = self._get_common_headers()
		
		response = self.http.get(
			self.ENDPOINTS["user_roles"],
			auth_header=self._get_auth_header(),
			headers=headers
		)
		
		return response
	
	# =========================================================================
	# API 3: Get All Config With Report Org List
	# =========================================================================
	
	def get_report_org_list(self, writing_config_code, per_map_user_role_id=None):
		"""
		Get connected report periods for organization.
		
		Args:
			writing_config_code: Report period code (e.g., "End_2024_H_2")
			per_map_user_role_id: User role ID (from get_user_roles)
			
		Returns:
			list: Connected report configurations
		"""
		role_id = per_map_user_role_id or self.settings.per_map_user_role_id
		
		headers = self._get_common_headers(
			writingConfigCode=writing_config_code,
			perMapUserRoleID=str(role_id)
		)
		
		response = self.http.get(
			self.ENDPOINTS["report_org_list"],
			auth_header=self._get_auth_header(),
			headers=headers
		)
		
		return response
	
	# =========================================================================
	# API 4: Get Report User Org Hdr List (Report Requests)
	# =========================================================================
	
	def get_report_requests(self, report_writing_config_id, per_map_user_role_id=None):
		"""
		Get report requests/submissions for a period.
		
		Args:
			report_writing_config_id: Report period ID
			per_map_user_role_id: User role ID
			
		Returns:
			list: Report requests with status
		"""
		role_id = per_map_user_role_id or self.settings.per_map_user_role_id
		
		headers = self._get_common_headers(
			reportWritingConfigId=str(report_writing_config_id),
			perMapUserRoleID=str(role_id)
		)
		
		response = self.http.get(
			self.ENDPOINTS["report_requests"],
			auth_header=self._get_auth_header(),
			headers=headers
		)
		
		return response
	
	# =========================================================================
	# API 5: Decide Report User Org Hdr (Start Report Entry)
	# =========================================================================
	
	def start_report_entry(self, report_writing_config_id, report_user_org_hdr_id,
						   per_map_user_role_id=None):
		"""
		Start/initialize report entry session.
		
		Args:
			report_writing_config_id: Report period ID
			report_user_org_hdr_id: Report request ID
			per_map_user_role_id: User role ID
			
		Returns:
			dict: Report package form map list (available forms)
		"""
		role_id = per_map_user_role_id or self.settings.per_map_user_role_id
		
		headers = self._get_common_headers(
			reportWritingConfigId=str(report_writing_config_id),
			reportUserOrgHdrId=str(report_user_org_hdr_id),
			perMapUserRoleID=str(role_id)
		)
		
		response = self.http.get(
			self.ENDPOINTS["decide_report"],
			auth_header=self._get_auth_header(),
			headers=headers
		)
		
		return response
	
	# =========================================================================
	# API 6: Get Report Data (Form + Validation Rules)
	# =========================================================================
	
	def get_report_data(self, report_writing_config_id, report_user_org_hdr_id,
						per_map_user_role_id=None):
		"""
		Get report form data including validation rules and existing values.
		
		Args:
			report_writing_config_id: Report period ID
			report_user_org_hdr_id: Report request ID
			per_map_user_role_id: User role ID
			
		Returns:
			dict: Report data with forms, columns, rows, and check expressions
		"""
		role_id = per_map_user_role_id or self.settings.per_map_user_role_id
		
		headers = self._get_common_headers(
			reportWritingConfigId=str(report_writing_config_id),
			reportUserOrgHdrId=str(report_user_org_hdr_id),
			perMapUserRoleID=str(role_id)
		)
		
		response = self.http.get(
			self.ENDPOINTS["report_data"],
			auth_header=self._get_auth_header(),
			headers=headers
		)
		
		if response.get("statusCode") == 200:
			return response.get("result", {})
		
		return response
	
	# =========================================================================
	# API 7: Get Report Package Map (Form Names)
	# =========================================================================
	
	def get_report_package_map(self, report_user_org_hdr_id, per_map_user_role_id=None):
		"""
		Get report form package map (form hierarchy and names).
		
		Args:
			report_user_org_hdr_id: Report request ID
			per_map_user_role_id: User role ID
			
		Returns:
			dict: Report package form map with form codes and names
		"""
		role_id = per_map_user_role_id or self.settings.per_map_user_role_id
		
		headers = self._get_common_headers(
			reportUserOrgHdrId=str(report_user_org_hdr_id),
			perMapUserRoleID=str(role_id)
		)
		
		response = self.http.get(
			self.ENDPOINTS["report_package_map"],
			auth_header=self._get_auth_header(),
			headers=headers
		)
		
		return response
	
	# =========================================================================
	# API 8: Save Report Data (Draft)
	# =========================================================================
	
	def save_report_data(self, report_user_org_hdr_id, cell_data):
		"""
		Save report data as draft.
		
		Args:
			report_user_org_hdr_id: Report request ID
			cell_data: List of cell values to save
				[{"id": 205914, "cellValue": "100"}, ...]
			
		Returns:
			dict: Save result
		"""
		payload = {
			"reportUserOrgHdrId": report_user_org_hdr_id,
			"cellModelList": cell_data
		}
		
		response = self.http.post(
			self.ENDPOINTS["save_report"],
			auth_header=self._get_auth_header(),
			json=payload
		)
		
		return response
	
	# =========================================================================
	# API 9: Send Report Data (Submit Final)
	# =========================================================================
	
	def send_report(self, report_user_org_hdr_id, per_map_user_role_id=None):
		"""
		Submit final report for approval.
		
		Args:
			report_user_org_hdr_id: Report request ID
			per_map_user_role_id: User role ID
			
		Returns:
			dict: Submission result with validation info
				- validExpKeys: Failed validation expression keys
				- validCellKeys: Failed cell validation keys
		"""
		role_id = per_map_user_role_id or self.settings.per_map_user_role_id
		
		headers = self._get_common_headers(
			perMapUserRoleID=str(role_id)
		)
		
		payload = {
			"reportUserOrgHdrId": report_user_org_hdr_id
		}
		
		response = self.http.post(
			self.ENDPOINTS["send_report"],
			auth_header=self._get_auth_header(),
			headers=headers,
			json=payload
		)
		
		# Log submission
		self._log_submission(report_user_org_hdr_id, response)
		
		return response
	
	# =========================================================================
	# API 10: Get Confirmed Report Data
	# =========================================================================
	
	def get_confirmed_report(self, writing_config_code, org_reg_no=None, description=None):
		"""
		Query confirmed/approved financial report data.
		
		Note: Requires CEO approval in eBalance system first.
		
		Args:
			writing_config_code: Report period code
			org_reg_no: Organization registration number (optional)
			description: Description/notes (optional)
			
		Returns:
			dict: Confirmed report data with all form values
		"""
		headers = {
			"writingConfigCode": writing_config_code,
			"orgRegNo": org_reg_no or self.settings.org_regno
		}
		
		if description:
			headers["description"] = description
		
		response = self.http.get(
			self.ENDPOINTS["confirmed_report"],
			auth_header=self._get_auth_header(),
			headers=headers
		)
		
		if response.get("statusCode") == 200:
			return response.get("result", {})
		
		return response
	
	# =========================================================================
	# Helper Methods
	# =========================================================================
	
	def test_connection(self):
		"""
		Test API connection and credentials.
		
		Returns:
			dict: Connection test result with status and message
		"""
		try:
			# Test 1: Auth token
			token = self.auth.get_token(force_refresh=True)
			if not token:
				return {"success": False, "message": "Failed to get auth token"}
			
			# Test 2: Get user roles
			roles = self.get_user_roles()
			if roles:
				# Extract and store perMapUserRoleId
				role_id = None
				if isinstance(roles, list) and roles:
					role_id = roles[0].get("id") or roles[0].get("perMapUserRoleId")
				elif isinstance(roles, dict):
					role_id = roles.get("id") or roles.get("perMapUserRoleId")
				
				if role_id:
					# Store in settings
					frappe.db.set_value(
						"eBalance Settings",
						"eBalance Settings",
						"per_map_user_role_id",
						str(role_id)
					)
					frappe.db.commit()
				
				return {
					"success": True,
					"message": "Connection successful",
					"user_roles": roles,
					"per_map_user_role_id": role_id
				}
			
			return {"success": True, "message": "Auth successful, roles check pending"}
			
		except EBalanceAuthError as e:
			return {"success": False, "message": f"Auth error: {str(e)}"}
		except EBalanceHTTPError as e:
			return {"success": False, "message": f"API error: {str(e)}"}
		except Exception as e:
			return {"success": False, "message": f"Error: {str(e)}"}
	
	def _log_submission(self, report_id, response):
		"""Log report submission to eBalance Submission Log"""
		try:
			if frappe.db.exists("DocType", "eBalance Submission Log"):
				log = frappe.new_doc("eBalance Submission Log")
				log.report_user_org_hdr_id = str(report_id)
				log.response_data = frappe.as_json(response)
				log.status = "Submitted" if not response.get("validExpKeys") else "Validation Failed"
				log.insert(ignore_permissions=True)
				frappe.db.commit()
		except Exception:
			pass  # Non-critical
	
	def close(self):
		"""Close client connections"""
		if self.http:
			self.http.close()


# Convenience function
def get_client():
	"""Get EBalanceClient instance"""
	return EBalanceClient()


# Frappe whitelisted API methods
@frappe.whitelist()
def test_connection():
	"""Test eBalance API connection"""
	client = get_client()
	try:
		return client.test_connection()
	finally:
		client.close()


@frappe.whitelist()
def get_report_periods():
	"""Get available report periods"""
	client = get_client()
	try:
		return client.get_writing_configs()
	finally:
		client.close()


@frappe.whitelist()
def sync_user_roles():
	"""Sync user roles and get perMapUserRoleId"""
	client = get_client()
	try:
		return client.get_user_roles()
	finally:
		client.close()
