# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt

"""
eBalance App Installation and Setup
Handles after_install and after_migrate hooks
"""

import frappe
from frappe import _


def after_install():
    """
    Run after app installation
    - Create default eBalance Settings
    - Set up permissions
    - Create workspace if needed
    """
    create_default_settings()
    setup_permissions()
    create_custom_fields()
    frappe.db.commit()
    
    print("✅ eBalance app installed successfully!")
    print("   - Configure eBalance Settings to connect to MOF")
    print("   - Sync report periods to begin reporting")


def after_migrate():
    """
    Run after bench migrate
    - Update custom fields
    - Sync permissions
    """
    create_custom_fields()
    sync_fixtures()
    frappe.db.commit()


def before_uninstall():
    """
    Run before app uninstallation
    - Clean up custom fields
    - Remove settings
    """
    cleanup_custom_fields()


def create_default_settings():
    """Create default eBalance Settings if not exists"""
    if not frappe.db.exists("eBalance Settings", "eBalance Settings"):
        doc = frappe.get_doc({
            "doctype": "eBalance Settings",
            "enabled": 0,
            "environment": "Staging",
            "auth_url": "https://auth.itc.gov.mn/auth/realms/ITC",
            "staging_url": "https://st-inspector-ebalance.mof.gov.mn",
            "production_url": "https://inspector-ebalance.mof.gov.mn",
            "token_timeout": 3600,
            "auto_sync_periods": 1,
            "auto_sync_interval": "Daily",
            "retry_count": 3,
            "retry_delay": 5,
            "request_timeout": 30,
            "log_retention_days": 90
        })
        doc.insert(ignore_permissions=True)
        print("✅ Created default eBalance Settings")


def setup_permissions():
    """Set up role permissions for eBalance doctypes"""
    # Roles that should have access to eBalance
    manager_roles = ["System Manager", "Accounts Manager"]
    user_roles = ["Accounts User", "Accounts Manager", "System Manager"]
    
    doctypes = {
        "eBalance Settings": {
            "roles": manager_roles,
            "perms": {"read": 1, "write": 1, "create": 0}
        },
        "eBalance Report Period": {
            "roles": user_roles,
            "perms": {"read": 1, "write": 1, "create": 1, "delete": 1}
        },
        "eBalance Report Request": {
            "roles": user_roles,
            "perms": {"read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1}
        },
        "eBalance Submission Log": {
            "roles": user_roles,
            "perms": {"read": 1, "write": 0, "create": 0}
        }
    }
    
    for doctype, config in doctypes.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        
        for role in config["roles"]:
            if not frappe.db.exists("Role", role):
                continue
            
            # Check if permission already exists
            existing = frappe.db.exists("Custom DocPerm", {
                "parent": doctype,
                "role": role
            })
            
            if not existing:
                try:
                    frappe.get_doc({
                        "doctype": "Custom DocPerm",
                        "parent": doctype,
                        "parenttype": "DocType",
                        "parentfield": "permissions",
                        "role": role,
                        **config["perms"]
                    }).insert(ignore_permissions=True)
                except Exception:
                    pass  # Permission might already exist
    
    print("✅ Set up eBalance permissions")


def create_custom_fields():
    """Create custom fields for ERPNext integration"""
    custom_fields = {
        "Company": [
            {
                "fieldname": "ebalance_section",
                "label": "eBalance Integration",
                "fieldtype": "Section Break",
                "insert_after": "default_letter_head",
                "collapsible": 1
            },
            {
                "fieldname": "ebalance_enabled",
                "label": "Enable eBalance Reporting",
                "fieldtype": "Check",
                "insert_after": "ebalance_section",
                "description": "Enable MOF financial reporting for this company"
            },
            {
                "fieldname": "ebalance_org_id",
                "label": "eBalance Org ID",
                "fieldtype": "Data",
                "insert_after": "ebalance_enabled",
                "read_only": 1,
                "description": "Organization ID from MOF eBalance system"
            }
        ],
        "Fiscal Year": [
            {
                "fieldname": "ebalance_synced",
                "label": "eBalance Synced",
                "fieldtype": "Check",
                "insert_after": "disabled",
                "read_only": 1,
                "description": "Indicates if this fiscal year has been synced with eBalance"
            }
        ]
    }
    
    for doctype, fields in custom_fields.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        
        for field in fields:
            field_name = f"{doctype}-{field['fieldname']}"
            
            if not frappe.db.exists("Custom Field", field_name):
                try:
                    cf = frappe.get_doc({
                        "doctype": "Custom Field",
                        "dt": doctype,
                        "module": "eBalance",
                        **field
                    })
                    cf.insert(ignore_permissions=True)
                except Exception as e:
                    print(f"Warning: Could not create custom field {field_name}: {e}")
    
    print("✅ Created eBalance custom fields")


def cleanup_custom_fields():
    """Remove custom fields created by eBalance"""
    custom_fields = frappe.db.get_all(
        "Custom Field",
        filters={"module": "eBalance"},
        pluck="name"
    )
    
    for field in custom_fields:
        try:
            frappe.delete_doc("Custom Field", field, ignore_permissions=True)
        except Exception:
            pass
    
    print("✅ Cleaned up eBalance custom fields")


def sync_fixtures():
    """Sync fixture data after migration"""
    # Sync property setters if any
    pass


def setup_scheduler():
    """Set up scheduled tasks for eBalance"""
    # This is handled via hooks.py scheduler_events
    pass
