# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false

import frappe
from frappe.model.document import Document


class eBalanceSettings(Document):
	"""
	eBalance Settings - Single DocType for eBalance configuration.
	
	Credentials are stored encrypted using Frappe's Password field type.
	Never log or expose password values.
	"""
	
	# Auth URL mapping
	AUTH_URLS = {
		"Staging": "https://st.auth.itc.gov.mn/auth/realms/Staging",
		"Production": "https://auth.itc.gov.mn/auth/realms/ITC"
	}
	
	# API URL mapping
	API_URLS = {
		"Staging": "https://st-inspector-ebalance.mof.gov.mn",
		"Production": "https://inspector-ebalance.mof.gov.mn"
	}
	
	def validate(self):
		"""Validate settings before save"""
		self._set_urls()
		self._set_user_regno()
		self._validate_org_regno()
	
	def _set_urls(self):
		"""Set auth and API URLs based on environment"""
		env = self.environment or "Staging"
		self.auth_url = self.AUTH_URLS.get(env, self.AUTH_URLS["Staging"])
		self.api_url = self.API_URLS.get(env, self.API_URLS["Staging"])
	
	def _set_user_regno(self):
		"""Set user_regno from username if not specified"""
		if not self.user_regno and self.username:
			self.user_regno = self.username
	
	def _validate_org_regno(self):
		"""Validate organization registration number"""
		if self.org_regno:
			# Remove any spaces
			self.org_regno = self.org_regno.strip()
			# Validate format (typically 7 digits for legal entities)
			if not self.org_regno.isdigit():
				frappe.throw("Organization RegNo must be numeric")
	
	def on_update(self):
		"""After save actions"""
		# Clear cached token if credentials changed
		if self.has_value_changed("username") or self.has_value_changed("password"):
			self._clear_token_cache()
	
	def _clear_token_cache(self):
		"""Clear stored token when credentials change"""
		frappe.db.set_value(
			"eBalance Settings",
			"eBalance Settings",
			{
				"access_token": "",
				"token_expiry": None,
				"refresh_token": "",
				"per_map_user_role_id": ""
			},
			update_modified=False
		)
	
	@frappe.whitelist()
	def test_connection(self):
		"""Test API connection"""
		from ebalance.api.client import get_client
		
		client = get_client()
		try:
			result = client.test_connection()
			
			if result.get("success"):
				self.connection_status = "✅ Connected"
				frappe.msgprint(
					f"Connection successful!<br>Role ID: {result.get('per_map_user_role_id', 'N/A')}",
					title="eBalance Connection",
					indicator="green"
				)
			else:
				self.connection_status = f"❌ {result.get('message', 'Failed')}"
				frappe.msgprint(
					result.get("message", "Connection failed"),
					title="eBalance Connection Error",
					indicator="red"
				)
			
			self.save()
			return result
			
		except Exception as e:
			self.connection_status = f"❌ Error: {str(e)}"
			self.save()
			frappe.throw(str(e))
		finally:
			client.close()
	
	@frappe.whitelist()
	def sync_report_periods(self):
		"""Sync available report periods from eBalance"""
		from ebalance.api.client import get_client
		
		client = get_client()
		try:
			periods = client.get_writing_configs()
			
			# Create/update eBalance Report Period records
			created = 0
			updated = 0
			
			for period in periods:
				code = period.get("code")
				name = period.get("name")
				
				if frappe.db.exists("eBalance Report Period", {"period_code": code}):
					# Update existing
					doc = frappe.get_doc("eBalance Report Period", {"period_code": code})
					doc.period_name = name
					doc.save(ignore_permissions=True)
					updated += 1
				else:
					# Create new
					doc = frappe.new_doc("eBalance Report Period")
					doc.period_code = code
					doc.period_name = name
					doc.insert(ignore_permissions=True)
					created += 1
			
			# Update last sync time
			self.last_sync = frappe.utils.now()
			self.save()
			
			frappe.msgprint(
				f"Synced {len(periods)} periods. Created: {created}, Updated: {updated}",
				title="eBalance Sync Complete",
				indicator="green"
			)
			
			return {"created": created, "updated": updated, "total": len(periods)}
			
		except Exception as e:
			frappe.throw(f"Sync failed: {str(e)}")
		finally:
			client.close()


def get_settings():
	"""Get eBalance Settings singleton"""
	return frappe.get_single("eBalance Settings")
