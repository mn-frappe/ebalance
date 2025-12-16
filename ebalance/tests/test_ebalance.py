# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false

"""
eBalance Basic Tests
Verifies core functionality
"""

import frappe
from frappe.tests import IntegrationTestCase


class TestEBalanceBasic(IntegrationTestCase):
    """Basic tests for eBalance app"""
    
    def test_app_installed(self):
        """Test that eBalance app is properly installed"""
        # Check if the app is in installed apps
        installed_apps = frappe.get_installed_apps()
        self.assertIn("ebalance", installed_apps)
    
    def test_doctype_exists(self):
        """Test that eBalance Settings DocType exists"""
        self.assertTrue(
            frappe.db.exists("DocType", "eBalance Settings")
        )
    
    def test_settings_singleton(self):
        """Test that eBalance Settings is a single DocType"""
        doctype = frappe.get_doc("DocType", "eBalance Settings")
        self.assertTrue(doctype.issingle)
    
    def test_report_period_doctype(self):
        """Test that eBalance Report Period DocType exists"""
        self.assertTrue(
            frappe.db.exists("DocType", "eBalance Report Period")
        )
