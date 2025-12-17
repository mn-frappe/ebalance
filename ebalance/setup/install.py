# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

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
    - Add to Integrations workspace
    - Import MOF standard accounts
    """
    create_default_settings()
    setup_permissions()
    create_custom_fields()
    add_to_integrations_workspace()
    import_mof_accounts()
    frappe.db.commit()
    
    print("✅ eBalance app installed successfully!")
    print("   - Configure eBalance Settings to connect to MOF")
    print("   - Sync report periods to begin reporting")
    print("   - MOF Standard Chart of Accounts (154) imported")


def after_migrate():
    """
    Run after bench migrate
    - Update custom fields
    - Sync permissions
    - Ensure eBalance is in Integrations workspace
    - Import any missing MOF accounts
    """
    create_custom_fields()
    sync_fixtures()
    add_to_integrations_workspace()
    import_mof_accounts()
    frappe.db.commit()


def before_uninstall():
    """
    Run before app uninstallation
    - Clean up custom fields
    - Remove from Integrations workspace
    """
    cleanup_custom_fields()
    remove_from_integrations_workspace()


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


def add_to_integrations_workspace():
    """
    Add eBalance Settings link to MN Settings section in Integrations workspace.
    
    Creates a "MN Settings" card section if it doesn't exist (for when eBalance
    is installed before QPay/eBarimt), then adds eBalance Settings link.
    
    Properly calculates idx to avoid conflicts with other apps.
    Also updates the content JSON which controls the visual layout.
    """
    import json
    
    if not frappe.db.exists("Workspace", "Integrations"):
        return
    
    try:
        ws = frappe.get_doc("Workspace", "Integrations")
        
        # Get the maximum idx to avoid conflicts
        max_idx = max([link.idx or 0 for link in ws.links] or [0])
        
        # Check if MN Settings card already exists and get its position
        mn_card_idx = None
        for link in ws.links:
            if link.label == "MN Settings" and link.type == "Card Break":
                mn_card_idx = link.idx
                break
        
        if mn_card_idx is None:
            # Add MN Settings card break at the end
            max_idx += 1
            ws.append(
                "links",
                {
                    "type": "Card Break",
                    "label": "MN Settings",
                    "hidden": 0,
                    "is_query_report": 0,
                    "link_count": 0,
                    "onboard": 0,
                    "idx": max_idx,
                },
            )
            mn_card_idx = max_idx
        
        # Check if eBalance Settings link already exists
        ebalance_link_exists = any(
            link.link_to == "eBalance Settings" and link.type == "Link"
            for link in ws.links
        )
        
        if not ebalance_link_exists:
            # Add eBalance Settings link right after MN Settings card
            max_idx = max([link.idx or 0 for link in ws.links] or [0]) + 1
            ws.append(
                "links",
                {
                    "type": "Link",
                    "label": "eBalance Settings",
                    "link_type": "DocType",
                    "link_to": "eBalance Settings",
                    "hidden": 0,
                    "is_query_report": 0,
                    "link_count": 0,
                    "onboard": 1,
                    "only_for": "",
                    "idx": max_idx,
                },
            )
        
        # Update content JSON to include MN Settings card (controls visual layout)
        if ws.content:
            content = json.loads(ws.content)
            mn_card_in_content = any(
                item.get("data", {}).get("card_name") == "MN Settings"
                for item in content
                if item.get("type") == "card"
            )
            if not mn_card_in_content:
                # Add MN Settings card to content
                content.append({
                    "id": frappe.generate_hash(length=10),
                    "type": "card",
                    "data": {"card_name": "MN Settings", "col": 4},
                })
                ws.content = json.dumps(content)
        
        ws.save(ignore_permissions=True)
        frappe.db.commit()
        print("  ✓ Added eBalance Settings to Integrations workspace (MN Settings section)")
    except Exception as e:
        print(f"  ⚠ Could not add to Integrations workspace: {e}")


def remove_from_integrations_workspace():
    """
    Remove eBalance Settings link from Integrations workspace during uninstall.
    """
    if not frappe.db.exists("Workspace", "Integrations"):
        return
    
    try:
        ws = frappe.get_doc("Workspace", "Integrations")
        
        # Remove eBalance Settings link
        ws.links = [
            link for link in ws.links
            if not (link.link_to == "eBalance Settings" and link.type == "Link")
        ]
        
        # Check if there are any MN Settings links left (QPay, eBarimt)
        mn_links = [
            link for link in ws.links
            if link.type == "Link" and link.link_to in ["QPay Settings", "eBarimt Settings"]
        ]
        
        # If no MN links left, remove the MN Settings card break
        if not mn_links:
            ws.links = [
                link for link in ws.links
                if not (link.label == "MN Settings" and link.type == "Card Break")
            ]
        
        ws.save(ignore_permissions=True)
        print("  ✓ Removed eBalance Settings from Integrations workspace")
    except Exception as e:
        print(f"  ⚠ Could not remove from Integrations workspace: {e}")


def import_mof_accounts():
    """
    Import MOF Standard Chart of Accounts (154 accounts from НББОУС).
    These are needed for MOF financial report generation.
    """
    try:
        # Check if MOF Account Mapping DocType exists
        if not frappe.db.exists("DocType", "MOF Account Mapping"):
            print("  ⚠ MOF Account Mapping DocType not found - skipping import")
            return
        
        from ebalance.fixtures.mof_accounts import import_mof_accounts as do_import
        result = do_import()
        
        if result["imported"] > 0:
            print(f"  ✓ Imported {result['imported']} MOF standard accounts")
        if result["skipped"] > 0:
            print(f"  ℹ Skipped {result['skipped']} existing accounts")
        if result["errors"]:
            print(f"  ⚠ {len(result['errors'])} errors during import")
            
    except Exception as e:
        print(f"  ⚠ Could not import MOF accounts: {e}")
