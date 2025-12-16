# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
ERPNext Period Closing Voucher Integration for eBalance
Handles period closing events for financial reporting
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_days


def on_submit(doc, method=None):
    """
    Handle Period Closing Voucher submission
    
    Args:
        doc: Period Closing Voucher document
        method: Event method name
    """
    if not _is_ebalance_enabled():
        return
    
    # Check if this period closing affects eBalance reporting
    settings = _get_settings()
    if not settings:
        return
    
    # Get linked company
    company = doc.company
    
    # Check if period has pending eBalance reports
    pending_reports = _get_pending_reports_for_period(company, doc.posting_date)
    
    if pending_reports:
        frappe.msgprint(
            _("Period closing affects {0} pending eBalance report(s). Please review.").format(
                len(pending_reports)
            ),
            indicator="orange",
            alert=True
        )
        
        # Update report status
        for report in pending_reports:
            frappe.db.set_value(
                "eBalance Report Request",
                report.name,
                "period_closed",
                1
            )


def on_cancel(doc, method=None):
    """
    Handle Period Closing Voucher cancellation
    
    Args:
        doc: Period Closing Voucher document
        method: Event method name
    """
    if not _is_ebalance_enabled():
        return
    
    # Check if period has submitted eBalance reports
    submitted_reports = frappe.db.get_all(
        "eBalance Report Request",
        filters={
            "company": doc.company,
            "period_end": ["<=", doc.posting_date],
            "status": "Submitted"
        },
        fields=["name"]
    )
    
    if submitted_reports:
        frappe.msgprint(
            _("Warning: {0} eBalance report(s) were submitted for this period").format(
                len(submitted_reports)
            ),
            indicator="red",
            alert=True
        )


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


def _get_pending_reports_for_period(company, posting_date):
    """
    Get pending eBalance reports for a period
    
    Args:
        company: Company name
        posting_date: Period closing date
        
    Returns:
        list: Pending report requests
    """
    return frappe.db.get_all(
        "eBalance Report Request",
        filters={
            "company": company,
            "period_end": ["<=", posting_date],
            "status": ["in", ["Draft", "Pending", "In Progress"]]
        },
        fields=["name", "period_name", "status"]
    )


def validate_period_closing_for_ebalance(company, fiscal_year, posting_date):
    """
    Validate if period can be closed for eBalance compliance
    
    Args:
        company: Company name
        fiscal_year: Fiscal year name
        posting_date: Period closing date
        
    Returns:
        dict: Validation result
    """
    issues = []
    warnings = []
    
    # Check for unsubmitted eBalance reports
    pending_reports = _get_pending_reports_for_period(company, posting_date)
    if pending_reports:
        warnings.append(
            _("{0} eBalance report(s) are pending for this period").format(
                len(pending_reports)
            )
        )
    
    # Check for draft journal entries
    draft_entries = frappe.db.count(
        "Journal Entry",
        {
            "company": company,
            "posting_date": ["<=", posting_date],
            "docstatus": 0
        }
    )
    if draft_entries > 0:
        warnings.append(
            _("{0} draft journal entries exist for this period").format(draft_entries)
        )
    
    # Check if trial balance is balanced
    from ebalance.integrations.trial_balance import get_trial_balance_for_ebalance
    
    fiscal_year_doc = frappe.get_doc("Fiscal Year", fiscal_year)
    trial_balance = get_trial_balance_for_ebalance(
        company,
        fiscal_year_doc.year_start_date,
        posting_date
    )
    
    totals = trial_balance.get("totals", {})
    debit_total = totals.get("closing_debit", 0)
    credit_total = totals.get("closing_credit", 0)
    
    if abs(debit_total - credit_total) > 0.01:
        issues.append(
            _("Trial balance is not balanced: Debit={0}, Credit={1}").format(
                debit_total, credit_total
            )
        )
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }


def get_period_closing_status(company, fiscal_year):
    """
    Get period closing status for eBalance reporting
    
    Args:
        company: Company name
        fiscal_year: Fiscal year name
        
    Returns:
        dict: Period closing status
    """
    # Get all period closing vouchers for the fiscal year
    pcv_list = frappe.db.get_all(
        "Period Closing Voucher",
        filters={
            "company": company,
            "fiscal_year": fiscal_year,
            "docstatus": 1
        },
        fields=["name", "posting_date", "closing_account_head"],
        order_by="posting_date asc"
    )
    
    # Get eBalance report requests
    report_requests = frappe.db.get_all(
        "eBalance Report Request",
        filters={
            "company": company,
            "fiscal_year": fiscal_year
        },
        fields=["name", "period_name", "status", "period_start", "period_end"]
    )
    
    return {
        "period_closings": pcv_list,
        "report_requests": report_requests,
        "periods_closed": len(pcv_list),
        "reports_submitted": len([r for r in report_requests if r.status == "Submitted"])
    }


@frappe.whitelist()
def create_ebalance_report_after_closing(period_closing_voucher):
    """
    Create eBalance report request after period closing
    
    Args:
        period_closing_voucher: Period Closing Voucher name
        
    Returns:
        dict: Created report request or None
    """
    frappe.has_permission("eBalance Report Request", "create", throw=True)
    
    pcv = frappe.get_doc("Period Closing Voucher", period_closing_voucher)
    
    # Check for existing report
    existing = frappe.db.exists(
        "eBalance Report Request",
        {
            "company": pcv.company,
            "period_end": pcv.posting_date
        }
    )
    
    if existing:
        return {"message": _("Report request already exists"), "name": existing}
    
    # Get fiscal year dates
    fiscal_year = frappe.get_doc("Fiscal Year", pcv.fiscal_year)
    
    # Determine period start (last closing date + 1 or fiscal year start)
    last_closing = frappe.db.get_value(
        "Period Closing Voucher",
        {
            "company": pcv.company,
            "fiscal_year": pcv.fiscal_year,
            "posting_date": ["<", pcv.posting_date],
            "docstatus": 1
        },
        "posting_date",
        order_by="posting_date desc"
    )
    
    period_start = add_days(last_closing, 1) if last_closing else fiscal_year.year_start_date
    
    # Create report request
    report = frappe.get_doc({
        "doctype": "eBalance Report Request",
        "company": pcv.company,
        "fiscal_year": pcv.fiscal_year,
        "period_name": f"{pcv.fiscal_year} - Period ending {pcv.posting_date}",
        "period_start": period_start,
        "period_end": pcv.posting_date,
        "status": "Draft",
        "period_closed": 1
    })
    report.insert()
    
    return {
        "message": _("Report request created successfully"),
        "name": report.name
    }
