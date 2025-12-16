# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
ERPNext GL Entry Integration for eBalance
Monitors general ledger changes for reporting
"""

import frappe
from frappe import _
from frappe.utils import getdate, flt


def on_update(doc, method=None):
    """
    Handle GL Entry update - check for eBalance reporting impact
    
    Args:
        doc: GL Entry document
        method: Event method name
    """
    if not _is_ebalance_enabled():
        return
    
    # Skip if not in a submitted state
    if doc.docstatus != 1:
        return
    
    # Check if this affects an active eBalance period
    _check_period_impact(doc)


def on_cancel(doc, method=None):
    """
    Handle GL Entry cancellation
    
    Args:
        doc: GL Entry document
        method: Event method name
    """
    if not _is_ebalance_enabled():
        return
    
    # Check if this affects a submitted eBalance report
    submitted_reports = frappe.db.get_all(
        "eBalance Report Request",
        filters={
            "company": doc.company,
            "period_start": ["<=", doc.posting_date],
            "period_end": [">=", doc.posting_date],
            "status": "Submitted"
        },
        fields=["name", "period_name"]
    )
    
    if submitted_reports:
        frappe.log_error(
            message=f"GL Entry {doc.name} cancelled after eBalance submission for periods: {submitted_reports}",
            title="eBalance: GL Entry Cancelled"
        )


def _is_ebalance_enabled():
    """Check if eBalance is enabled"""
    try:
        settings = frappe.get_cached_doc("eBalance Settings")
        return settings.enabled == 1
    except Exception:
        return False


def _check_period_impact(doc):
    """
    Check if GL Entry impacts an active eBalance period
    
    Args:
        doc: GL Entry document
    """
    # Find active report periods that include this posting date
    active_periods = frappe.db.get_all(
        "eBalance Report Request",
        filters={
            "company": doc.company,
            "period_start": ["<=", doc.posting_date],
            "period_end": [">=", doc.posting_date],
            "status": ["in", ["Draft", "In Progress"]]
        },
        fields=["name"]
    )
    
    # Update the modification timestamp on affected periods
    for period in active_periods:
        frappe.db.set_value(
            "eBalance Report Request",
            period.name,
            "last_gl_update",
            frappe.utils.now()
        )


def get_gl_summary_for_period(company, from_date, to_date, account=None):
    """
    Get GL summary for eBalance period
    
    Args:
        company: Company name
        from_date: Period start
        to_date: Period end
        account: Specific account (optional)
        
    Returns:
        dict: GL summary
    """
    filters = {
        "company": company,
        "posting_date": ["between", [from_date, to_date]],
        "is_cancelled": 0
    }
    
    if account:
        filters["account"] = account
    
    # Get aggregated data
    result = frappe.db.sql("""
        SELECT 
            account,
            SUM(debit) as total_debit,
            SUM(credit) as total_credit,
            SUM(debit - credit) as balance,
            COUNT(*) as entry_count
        FROM `tabGL Entry`
        WHERE 
            company = %(company)s
            AND posting_date BETWEEN %(from_date)s AND %(to_date)s
            AND is_cancelled = 0
            {account_filter}
        GROUP BY account
        ORDER BY account
    """.format(
        account_filter="AND account = %(account)s" if account else ""
    ), {
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "account": account
    }, as_dict=True)
    
    return {
        "accounts": result,
        "totals": {
            "total_debit": sum(r.total_debit or 0 for r in result),
            "total_credit": sum(r.total_credit or 0 for r in result),
            "entry_count": sum(r.entry_count or 0 for r in result)
        }
    }


def validate_gl_completeness(company, from_date, to_date):
    """
    Validate GL entries are complete for eBalance submission
    
    Args:
        company: Company name
        from_date: Period start
        to_date: Period end
        
    Returns:
        dict: Validation result
    """
    issues = []
    warnings = []
    
    # Check for unposted documents
    unposted_je = frappe.db.count(
        "Journal Entry",
        {
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "docstatus": 0
        }
    )
    if unposted_je > 0:
        warnings.append(
            _("{0} draft Journal Entries found").format(unposted_je)
        )
    
    # Check for pending invoices
    pending_si = frappe.db.count(
        "Sales Invoice",
        {
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "docstatus": 0
        }
    )
    if pending_si > 0:
        warnings.append(
            _("{0} draft Sales Invoices found").format(pending_si)
        )
    
    pending_pi = frappe.db.count(
        "Purchase Invoice",
        {
            "company": company,
            "posting_date": ["between", [from_date, to_date]],
            "docstatus": 0
        }
    )
    if pending_pi > 0:
        warnings.append(
            _("{0} draft Purchase Invoices found").format(pending_pi)
        )
    
    # Verify trial balance is balanced
    summary = get_gl_summary_for_period(company, from_date, to_date)
    totals = summary.get("totals", {})
    
    difference = abs(totals.get("total_debit", 0) - totals.get("total_credit", 0))
    if difference > 0.01:
        issues.append(
            _("GL entries are not balanced: difference of {0}").format(
                flt(difference, 2)
            )
        )
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "summary": summary
    }


@frappe.whitelist()
def get_period_gl_status(company, from_date, to_date):
    """
    Get GL status for eBalance period (API endpoint)
    
    Args:
        company: Company name
        from_date: Period start
        to_date: Period end
        
    Returns:
        dict: GL status
    """
    frappe.has_permission("GL Entry", throw=True)
    
    validation = validate_gl_completeness(company, from_date, to_date)
    summary = get_gl_summary_for_period(company, from_date, to_date)
    
    return {
        "validation": validation,
        "summary": summary,
        "ready_for_submission": validation.get("valid", False) and len(validation.get("warnings", [])) == 0
    }
