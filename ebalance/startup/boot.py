# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eBalance Boot Session Data
Data sent to browser on session start
"""

import frappe
from frappe import _


def boot_session(bootinfo):
    """
    Add eBalance data to boot session
    
    Args:
        bootinfo: Frappe boot info object
    """
    if frappe.session.user == "Guest":
        return
    
    bootinfo.ebalance = get_ebalance_boot_data()


def get_ebalance_boot_data():
    """
    Get eBalance data for browser session
    
    Returns:
        dict: eBalance session data
    """
    data = {
        "enabled": False,
        "environment": "Staging",
        "has_permission": False,
        "pending_reports": 0,
        "upcoming_deadlines": []
    }
    
    try:
        # Check if user has permission
        if not frappe.has_permission("eBalance Settings", "read"):
            return data
        
        data["has_permission"] = True
        
        # Get settings
        settings = frappe.get_cached_doc("eBalance Settings")
        data["enabled"] = bool(settings.enabled)
        data["environment"] = settings.environment
        
        if not settings.enabled:
            return data
        
        # Get pending reports count
        data["pending_reports"] = frappe.db.count(
            "eBalance Report Request",
            {
                "status": ["in", ["Draft", "In Progress", "Pending"]]
            }
        )
        
        # Get upcoming deadlines (next 14 days)
        from frappe.utils import getdate, add_days
        
        upcoming = frappe.db.get_all(
            "eBalance Report Period",
            filters={
                "status": "Active",
                "deadline": ["between", [getdate(), add_days(getdate(), 14)]]
            },
            fields=["period_name", "deadline"],
            order_by="deadline asc",
            limit=5
        )
        
        data["upcoming_deadlines"] = upcoming
        
    except Exception:
        pass
    
    return data


def get_notification_config():
    """
    Get notification configuration for eBalance
    
    Returns:
        dict: Notification config
    """
    return {
        "for_doctype": {
            "eBalance Report Request": {
                "status": ["in", ["Draft", "In Progress", "Pending"]]
            },
            "eBalance Report Period": {
                "status": "Active"
            }
        }
    }


def get_help_links():
    """
    Get help links for eBalance
    
    Returns:
        list: Help link configurations
    """
    return [
        {
            "label": _("eBalance Documentation"),
            "url": "https://docs.erpnext.com/ebalance",
            "description": _("Learn how to use eBalance integration")
        },
        {
            "label": _("MOF eBalance Portal"),
            "url": "https://inspector-ebalance.mof.gov.mn",
            "description": _("Ministry of Finance eBalance System")
        },
        {
            "label": _("Report Issues"),
            "url": "https://github.com/mn-frappe/ebalance/issues",
            "description": _("Report bugs or request features")
        }
    ]
