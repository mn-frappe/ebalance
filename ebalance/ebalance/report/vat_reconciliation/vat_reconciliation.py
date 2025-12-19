# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
VAT Reconciliation Report

Reconciles VAT data between:
- GL Entry VAT (from ERPNext accounting)
- eBarimt VAT (from tax authority receipts) - if available

This report helps identify discrepancies between:
1. VAT recorded in ERPNext GL
2. VAT receipts submitted to Mongolia Tax Authority via eBarimt

When eBarimt is not installed, this report shows GL VAT data only.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate


def execute(filters=None):
    """
    Execute the VAT Reconciliation Report.
    
    Args:
        filters: Report filters
        
    Returns:
        tuple: (columns, data, message, chart, report_summary)
    """
    filters = frappe._dict(filters or {})
    
    validate_filters(filters)
    
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart(data, filters)
    report_summary = get_summary(data, filters)
    message = get_message(filters)
    
    return columns, data, message, chart, report_summary


def validate_filters(filters):
    """Validate report filters."""
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are required"))
    
    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date"))


def get_columns(filters):
    """Get report columns."""
    columns = [
        {
            "fieldname": "source",
            "label": _("Source"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "category",
            "label": _("Category"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "vat_amount",
            "label": _("VAT Amount"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "taxable_amount",
            "label": _("Taxable Amount"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "total_amount",
            "label": _("Total Amount"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "count",
            "label": _("Count"),
            "fieldtype": "Int",
            "width": 80
        },
        {
            "fieldname": "difference",
            "label": _("Difference"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        }
    ]
    
    return columns


def get_data(filters):
    """Get report data."""
    from ebalance.integrations.ebarimt import reconcile_vat, is_ebarimt_available
    
    data = []
    
    # Get reconciliation data
    reconciliation = reconcile_vat(
        company=filters.company,
        from_date=filters.from_date,
        to_date=filters.to_date
    )
    
    gl_vat = reconciliation.get("gl_vat", {})
    ebarimt_vat = reconciliation.get("ebarimt_vat")
    comparison = reconciliation.get("comparison", {})
    
    # GL Output VAT Row
    data.append({
        "source": _("GL Entry"),
        "category": _("Output VAT (Sales)"),
        "vat_amount": flt(gl_vat.get("output_vat"), 2),
        "taxable_amount": 0,  # Not tracked at GL level
        "total_amount": 0,
        "count": 0,
        "difference": 0,
        "status": ""
    })
    
    # GL Input VAT Row
    data.append({
        "source": _("GL Entry"),
        "category": _("Input VAT (Purchases)"),
        "vat_amount": flt(gl_vat.get("input_vat"), 2),
        "taxable_amount": 0,
        "total_amount": 0,
        "count": 0,
        "difference": 0,
        "status": ""
    })
    
    # GL Net VAT Row
    data.append({
        "source": _("GL Entry"),
        "category": _("Net VAT Payable"),
        "vat_amount": flt(gl_vat.get("net_vat"), 2),
        "taxable_amount": 0,
        "total_amount": 0,
        "count": 0,
        "difference": 0,
        "status": "",
        "bold": 1
    })
    
    # Empty separator row
    data.append({})
    
    # eBarimt data (if available)
    if ebarimt_vat and ebarimt_vat.get("available"):
        totals = ebarimt_vat.get("totals", {})
        breakdown = ebarimt_vat.get("breakdown", {})
        
        # eBarimt B2B Row
        data.append({
            "source": _("eBarimt"),
            "category": _("B2B Receipts"),
            "vat_amount": flt(breakdown.get("b2b_vat"), 2),
            "taxable_amount": 0,
            "total_amount": 0,
            "count": 0,
            "difference": 0,
            "status": ""
        })
        
        # eBarimt B2C Row
        data.append({
            "source": _("eBarimt"),
            "category": _("B2C Receipts"),
            "vat_amount": flt(breakdown.get("b2c_vat"), 2),
            "taxable_amount": 0,
            "total_amount": 0,
            "count": 0,
            "difference": 0,
            "status": ""
        })
        
        # eBarimt Returns Row
        if flt(breakdown.get("return_vat")):
            data.append({
                "source": _("eBarimt"),
                "category": _("Returns (Credit Notes)"),
                "vat_amount": flt(breakdown.get("return_vat"), 2) * -1,
                "taxable_amount": 0,
                "total_amount": 0,
                "count": 0,
                "difference": 0,
                "status": ""
            })
        
        # eBarimt Total Row
        data.append({
            "source": _("eBarimt"),
            "category": _("Total VAT (Receipts)"),
            "vat_amount": flt(totals.get("vat_amount"), 2),
            "taxable_amount": 0,
            "total_amount": flt(totals.get("total_amount"), 2),
            "count": totals.get("receipt_count") or 0,
            "difference": 0,
            "status": "",
            "bold": 1
        })
        
        # Empty separator
        data.append({})
        
        # Reconciliation Row
        difference = flt(comparison.get("difference"), 2)
        status = _("✓ Reconciled") if reconciliation.get("reconciled") else _("⚠ Discrepancy")
        
        data.append({
            "source": _("Reconciliation"),
            "category": _("GL vs eBarimt Difference"),
            "vat_amount": 0,
            "taxable_amount": 0,
            "total_amount": 0,
            "count": 0,
            "difference": difference,
            "status": status,
            "bold": 1
        })
    else:
        # eBarimt not available
        data.append({
            "source": _("eBarimt"),
            "category": _("Not Available"),
            "vat_amount": 0,
            "taxable_amount": 0,
            "total_amount": 0,
            "count": 0,
            "difference": 0,
            "status": _("eBarimt app not installed")
        })
    
    # Add discrepancies if any
    discrepancies = reconciliation.get("discrepancies", [])
    if discrepancies:
        data.append({})
        data.append({
            "source": _("Discrepancies"),
            "category": "",
            "vat_amount": 0,
            "taxable_amount": 0,
            "total_amount": 0,
            "count": len(discrepancies),
            "difference": 0,
            "status": "",
            "bold": 1
        })
        
        for disc in discrepancies[:10]:  # Limit to first 10
            data.append({
                "source": "",
                "category": disc.get("description", ""),
                "vat_amount": flt(disc.get("amount"), 2),
                "taxable_amount": 0,
                "total_amount": 0,
                "count": 0,
                "difference": 0,
                "status": disc.get("type", "")
            })
    
    return data


def get_chart(data, filters):
    """Get chart data for the report."""
    from ebalance.integrations.ebarimt import reconcile_vat
    
    reconciliation = reconcile_vat(
        company=filters.company,
        from_date=filters.from_date,
        to_date=filters.to_date
    )
    
    gl_vat = reconciliation.get("gl_vat", {})
    ebarimt_vat = reconciliation.get("ebarimt_vat")
    
    labels = [_("Output VAT"), _("Input VAT"), _("Net VAT")]
    gl_values = [
        flt(gl_vat.get("output_vat"), 2),
        flt(gl_vat.get("input_vat"), 2),
        flt(gl_vat.get("net_vat"), 2)
    ]
    
    datasets = [
        {
            "name": _("GL Entry"),
            "values": gl_values
        }
    ]
    
    if ebarimt_vat and ebarimt_vat.get("available"):
        ebarimt_values = [
            flt(ebarimt_vat["totals"].get("vat_amount"), 2),
            0,  # eBarimt doesn't track input VAT
            flt(ebarimt_vat["totals"].get("vat_amount"), 2)
        ]
        datasets.append({
            "name": _("eBarimt"),
            "values": ebarimt_values
        })
    
    return {
        "data": {
            "labels": labels,
            "datasets": datasets
        },
        "type": "bar",
        "colors": ["#5e64ff", "#ff5858"]
    }


def get_summary(data, filters):
    """Get report summary cards."""
    from ebalance.integrations.ebarimt import reconcile_vat, is_ebarimt_available
    
    reconciliation = reconcile_vat(
        company=filters.company,
        from_date=filters.from_date,
        to_date=filters.to_date
    )
    
    gl_vat = reconciliation.get("gl_vat", {})
    comparison = reconciliation.get("comparison", {})
    
    summary = [
        {
            "value": frappe.format_value(
                flt(gl_vat.get("output_vat"), 2),
                {"fieldtype": "Currency"}
            ),
            "label": _("GL Output VAT"),
            "datatype": "Currency"
        },
        {
            "value": frappe.format_value(
                flt(gl_vat.get("input_vat"), 2),
                {"fieldtype": "Currency"}
            ),
            "label": _("GL Input VAT"),
            "datatype": "Currency"
        },
        {
            "value": frappe.format_value(
                flt(gl_vat.get("net_vat"), 2),
                {"fieldtype": "Currency"}
            ),
            "label": _("Net VAT Payable"),
            "datatype": "Currency",
            "indicator": "blue"
        }
    ]
    
    if reconciliation.get("ebarimt_available"):
        indicator = "green" if reconciliation.get("reconciled") else "red"
        summary.append({
            "value": frappe.format_value(
                abs(flt(comparison.get("difference"), 2)),
                {"fieldtype": "Currency"}
            ),
            "label": _("Difference"),
            "datatype": "Currency",
            "indicator": indicator
        })
    else:
        summary.append({
            "value": _("Not Installed"),
            "label": _("eBarimt Status"),
            "datatype": "Data",
            "indicator": "grey"
        })
    
    return summary


def get_message(filters):
    """Get report message/instructions."""
    from ebalance.integrations.ebarimt import is_ebarimt_available
    
    messages = []
    
    if not is_ebarimt_available():
        messages.append(
            _("<b>Note:</b> eBarimt app is not installed. "
              "This report shows GL VAT data only. "
              "Install eBarimt to enable VAT reconciliation with tax receipts.")
        )
    else:
        messages.append(
            _("This report compares VAT from ERPNext GL Entries with "
              "VAT receipts submitted to Mongolia Tax Authority via eBarimt.")
        )
    
    messages.append(
        _("<b>Period:</b> {0} to {1}").format(
            formatdate(filters.from_date),
            formatdate(filters.to_date)
        )
    )
    
    return "<br>".join(messages)
