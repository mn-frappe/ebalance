# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
ERPNext Company Integration for eBalance
Handles company registration syncing with MOF
"""

import frappe
from frappe import _


def on_update(doc, method=None):
    """
    Handle Company update - sync with eBalance if configured
    
    Args:
        doc: Company document
        method: Event method name
    """
    if not _is_ebalance_enabled():
        return
    
    # Check if company has eBalance configured
    settings = _get_settings()
    if not settings:
        return
    
    # Only process if company matches org_reg_no
    if doc.get("tax_id") and doc.tax_id == settings.org_reg_no:
        _update_company_ebalance_status(doc, settings)


def _is_ebalance_enabled():
    """Check if eBalance is enabled"""
    try:
        settings = frappe.get_cached_doc("eBalance Settings")
        return settings.enabled == 1
    except Exception:
        return False


def _get_settings():
    """Get eBalance Settings"""
    try:
        return frappe.get_cached_doc("eBalance Settings")
    except Exception:
        return None


def _update_company_ebalance_status(company_doc, settings):
    """
    Update company's eBalance integration status
    
    Args:
        company_doc: Company document
        settings: eBalance Settings document
    """
    try:
        # Verify connection with MOF
        from ebalance.api.client import EBalanceClient
        
        client = EBalanceClient()
        roles = client.get_user_roles()
        
        if roles:
            frappe.msgprint(
                _("Company {0} is connected to eBalance with {1} role(s)").format(
                    company_doc.name,
                    len(roles) if isinstance(roles, list) else 1
                ),
                indicator="green",
                alert=True
            )
    except Exception as e:
        frappe.log_error(
            message=f"eBalance company sync failed: {str(e)}",
            title="eBalance Company Integration Error"
        )


def get_ebalance_company():
    """
    Get the ERPNext company linked to eBalance
    
    Returns:
        str: Company name or None
    """
    settings = _get_settings()
    if not settings or not settings.org_reg_no:
        return None
    
    company = frappe.db.get_value(
        "Company",
        {"tax_id": settings.org_reg_no},
        "name"
    )
    
    return company


def validate_company_for_ebalance(company_name):
    """
    Validate if a company can be used for eBalance reporting
    
    Args:
        company_name: Company name
        
    Returns:
        dict: Validation result with status and message
    """
    company = frappe.get_doc("Company", company_name)
    
    issues = []
    
    if not company.tax_id:
        issues.append(_("Company does not have a Tax ID (Registration Number)"))
    
    if not company.default_currency or company.default_currency != "MNT":
        issues.append(_("Company should have MNT as default currency"))
    
    # Check for chart of accounts
    coa_count = frappe.db.count("Account", {"company": company_name})
    if coa_count < 10:
        issues.append(_("Company does not have a proper Chart of Accounts"))
    
    # Check for fiscal year
    fiscal_year = frappe.db.get_value(
        "Fiscal Year",
        {"disabled": 0},
        ["name", "year_start_date", "year_end_date"],
        as_dict=True
    )
    if not fiscal_year:
        issues.append(_("No active Fiscal Year found"))
    
    if issues:
        return {
            "valid": False,
            "message": _("Company validation failed"),
            "issues": issues
        }
    
    return {
        "valid": True,
        "message": _("Company is ready for eBalance reporting"),
        "issues": []
    }
