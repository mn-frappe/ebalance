# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBalance eBarimt Integration (Optional)

Provides VAT reconciliation between:
- eBalance GL Entry VAT data (from ERPNext accounting)
- eBarimt Receipt VAT data (from tax authority receipts)

This integration is OPTIONAL - eBalance works fully without eBarimt installed.
When eBarimt is available, this module enables VAT reconciliation reports.

Independence Pattern:
- Uses dynamic detection of eBarimt app
- Never imports eBarimt at module level
- Gracefully returns None when eBarimt unavailable
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate


def is_ebarimt_available() -> bool:
    """
    Check if eBarimt app is installed.
    
    Returns:
        bool: True if eBarimt is installed and enabled
    """
    try:
        installed_apps = frappe.get_installed_apps()
        if "ebarimt" not in installed_apps:
            return False
        
        # Also check if eBarimt is enabled
        if frappe.db.exists("DocType", "eBarimt Settings"):
            enabled = frappe.db.get_single_value("eBarimt Settings", "enabled")
            return bool(enabled)
        
        return False
    except Exception:
        return False


def get_ebarimt_vat_summary(
    company: str,
    from_date: str,
    to_date: str
) -> dict | None:
    """
    Get VAT summary from eBarimt receipts for a period.
    
    This function retrieves actual VAT amounts from receipts submitted
    to the Mongolian Tax Authority via eBarimt.
    
    Args:
        company: Company name
        from_date: Period start date (YYYY-MM-DD)
        to_date: Period end date (YYYY-MM-DD)
        
    Returns:
        dict: VAT summary with totals and details, or None if eBarimt unavailable
    """
    if not is_ebarimt_available():
        return None
    
    # Query eBarimt Receipt Log for VAT data
    # Only include successful receipts
    receipts = frappe.db.sql("""
        SELECT 
            SUM(vat_amount) as total_vat,
            SUM(total_amount) as total_amount,
            SUM(CASE WHEN bill_type = 'B2B_RECEIPT' THEN vat_amount ELSE 0 END) as b2b_vat,
            SUM(CASE WHEN bill_type = 'B2C_RECEIPT' THEN vat_amount ELSE 0 END) as b2c_vat,
            COUNT(*) as receipt_count,
            SUM(CASE WHEN is_return = 1 THEN vat_amount ELSE 0 END) as return_vat
        FROM `tabeBarimt Receipt Log`
        WHERE status = 'Success'
            AND DATE(receipt_date) BETWEEN %s AND %s
    """, (from_date, to_date), as_dict=True)
    
    if not receipts or not receipts[0]:
        return {
            "available": True,
            "period": {"from_date": from_date, "to_date": to_date},
            "totals": {
                "vat_amount": 0,
                "total_amount": 0,
                "receipt_count": 0
            },
            "breakdown": {}
        }
    
    result = receipts[0]
    
    # Get daily breakdown for charting
    daily = frappe.db.sql("""
        SELECT 
            DATE(receipt_date) as date,
            SUM(vat_amount) as vat_amount,
            COUNT(*) as count
        FROM `tabeBarimt Receipt Log`
        WHERE status = 'Success'
            AND DATE(receipt_date) BETWEEN %s AND %s
        GROUP BY DATE(receipt_date)
        ORDER BY date
    """, (from_date, to_date), as_dict=True)
    
    return {
        "available": True,
        "period": {"from_date": from_date, "to_date": to_date},
        "totals": {
            "vat_amount": flt(result.get("total_vat"), 2),
            "total_amount": flt(result.get("total_amount"), 2),
            "receipt_count": result.get("receipt_count") or 0
        },
        "breakdown": {
            "b2b_vat": flt(result.get("b2b_vat"), 2),
            "b2c_vat": flt(result.get("b2c_vat"), 2),
            "return_vat": flt(result.get("return_vat"), 2)
        },
        "daily": daily
    }


def get_ebarimt_receipts_for_reconciliation(
    company: str,
    from_date: str,
    to_date: str,
    include_details: bool = False
) -> list | None:
    """
    Get eBarimt receipts for reconciliation with GL entries.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        include_details: Whether to include full receipt details
        
    Returns:
        list: Receipt records, or None if eBarimt unavailable
    """
    if not is_ebarimt_available():
        return None
    
    fields = [
        "name",
        "receipt_id",
        "sales_invoice",
        "pos_invoice",
        "receipt_date",
        "total_amount",
        "vat_amount",
        "bill_type",
        "status",
        "is_return"
    ]
    
    if include_details:
        fields.extend([
            "customer_tin",
            "merchant_tin",
            "lottery_number",
            "payment_type"
        ])
    
    receipts = frappe.get_all(
        "eBarimt Receipt Log",
        filters={
            "status": "Success",
            "receipt_date": ["between", [from_date, to_date]]
        },
        fields=fields,
        order_by="receipt_date"
    )
    
    return receipts


def reconcile_vat(
    company: str,
    from_date: str,
    to_date: str
) -> dict:
    """
    Reconcile VAT between GL Entries and eBarimt receipts.
    
    Compares:
    - GL Entry VAT (from ERPNext accounting)
    - eBarimt VAT (from tax authority receipts)
    
    Identifies discrepancies that need investigation.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        
    Returns:
        dict: Reconciliation result with matches and discrepancies
    """
    from ebalance.integrations.gl_entry import get_gl_summary_for_period
    
    # Get GL-based VAT
    gl_data = get_gl_summary_for_period(company, from_date, to_date)
    
    # Calculate VAT from GL (look for VAT accounts)
    gl_vat = _calculate_gl_vat(company, from_date, to_date)
    
    # Get eBarimt VAT (if available)
    ebarimt_data = get_ebarimt_vat_summary(company, from_date, to_date)
    
    result = {
        "period": {"from_date": from_date, "to_date": to_date},
        "company": company,
        "gl_vat": gl_vat,
        "ebarimt_available": ebarimt_data is not None,
        "ebarimt_vat": ebarimt_data,
        "reconciled": False,
        "discrepancies": []
    }
    
    if not ebarimt_data:
        result["message"] = _("eBarimt not available - showing GL VAT only")
        return result
    
    # Compare totals
    gl_total = flt(gl_vat.get("output_vat", 0), 2)
    ebarimt_total = flt(ebarimt_data["totals"]["vat_amount"], 2)
    
    difference = flt(gl_total - ebarimt_total, 2)
    
    result["comparison"] = {
        "gl_vat_total": gl_total,
        "ebarimt_vat_total": ebarimt_total,
        "difference": difference,
        "difference_percent": flt(difference / gl_total * 100, 2) if gl_total else 0
    }
    
    # Check for discrepancies
    tolerance = 0.01  # Allow 1 tugrik tolerance for rounding
    
    if abs(difference) <= tolerance:
        result["reconciled"] = True
        result["message"] = _("VAT reconciled successfully")
    else:
        result["reconciled"] = False
        result["discrepancies"].append({
            "type": "amount_mismatch",
            "description": _("GL VAT ({0}) does not match eBarimt VAT ({1})").format(
                frappe.format_value(gl_total, {"fieldtype": "Currency"}),
                frappe.format_value(ebarimt_total, {"fieldtype": "Currency"})
            ),
            "gl_amount": gl_total,
            "ebarimt_amount": ebarimt_total,
            "difference": difference
        })
        
        # Try to identify specific discrepancies
        discrepancies = _find_specific_discrepancies(company, from_date, to_date)
        result["discrepancies"].extend(discrepancies)
    
    return result


def _calculate_gl_vat(company: str, from_date: str, to_date: str) -> dict:
    """
    Calculate VAT from GL Entries.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        
    Returns:
        dict: GL VAT summary
    """
    # Find VAT accounts by common naming patterns
    vat_accounts = frappe.get_all(
        "Account",
        filters={
            "company": company,
            "account_type": "Tax",
            "is_group": 0
        },
        fields=["name", "account_name"]
    )
    
    output_vat = flt(0)
    input_vat = flt(0)
    
    for account in vat_accounts:
        name_lower = account.account_name.lower()
        
        # Get account balance for period
        balance = frappe.db.sql("""
            SELECT 
                SUM(credit) - SUM(debit) as balance
            FROM `tabGL Entry`
            WHERE account = %s
                AND company = %s
                AND posting_date BETWEEN %s AND %s
                AND is_cancelled = 0
        """, (account.name, company, from_date, to_date))
        
        account_balance = flt(balance[0][0]) if balance and balance[0][0] else 0
        
        # Classify as Output or Input VAT
        if any(kw in name_lower for kw in ["output", "payable", "борлуулалт", "төлөх"]):
            output_vat += account_balance
        elif any(kw in name_lower for kw in ["input", "receivable", "авлага", "авах"]):
            input_vat += abs(account_balance)  # Input VAT is typically debit balance
    
    return {
        "output_vat": flt(output_vat, 2),
        "input_vat": flt(input_vat, 2),
        "net_vat": flt(output_vat - input_vat, 2)
    }


def _find_specific_discrepancies(
    company: str,
    from_date: str,
    to_date: str
) -> list:
    """
    Find specific discrepancies between GL and eBarimt.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        
    Returns:
        list: Specific discrepancy records
    """
    if not is_ebarimt_available():
        return []
    
    discrepancies = []
    
    # Find invoices without eBarimt receipts
    invoices_without_receipt = frappe.db.sql("""
        SELECT 
            si.name,
            si.posting_date,
            si.grand_total,
            si.total_taxes_and_charges as vat_amount
        FROM `tabSales Invoice` si
        LEFT JOIN `tabeBarimt Receipt Log` erl 
            ON erl.sales_invoice = si.name AND erl.status = 'Success'
        WHERE si.company = %s
            AND si.posting_date BETWEEN %s AND %s
            AND si.docstatus = 1
            AND si.total_taxes_and_charges > 0
            AND erl.name IS NULL
        LIMIT 20
    """, (company, from_date, to_date), as_dict=True)
    
    for inv in invoices_without_receipt:
        discrepancies.append({
            "type": "missing_receipt",
            "description": _("Sales Invoice {0} has no eBarimt receipt").format(inv.name),
            "reference_doctype": "Sales Invoice",
            "reference_name": inv.name,
            "amount": flt(inv.vat_amount, 2)
        })
    
    # Find receipts without matching invoices
    orphan_receipts = frappe.db.sql("""
        SELECT 
            erl.name,
            erl.receipt_id,
            erl.receipt_date,
            erl.vat_amount
        FROM `tabeBarimt Receipt Log` erl
        LEFT JOIN `tabSales Invoice` si ON si.name = erl.sales_invoice
        WHERE erl.status = 'Success'
            AND DATE(erl.receipt_date) BETWEEN %s AND %s
            AND (erl.sales_invoice IS NULL OR si.name IS NULL)
            AND erl.pos_invoice IS NULL
        LIMIT 20
    """, (from_date, to_date), as_dict=True)
    
    for receipt in orphan_receipts:
        discrepancies.append({
            "type": "orphan_receipt",
            "description": _("eBarimt receipt {0} has no matching invoice").format(
                receipt.receipt_id or receipt.name
            ),
            "reference_doctype": "eBarimt Receipt Log",
            "reference_name": receipt.name,
            "amount": flt(receipt.vat_amount, 2)
        })
    
    return discrepancies


@frappe.whitelist()
def get_reconciliation_data(company: str, from_date: str, to_date: str) -> dict:
    """
    API endpoint for VAT reconciliation data.
    
    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        
    Returns:
        dict: Reconciliation data for the report
    """
    return reconcile_vat(company, from_date, to_date)
