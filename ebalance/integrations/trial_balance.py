# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
ERPNext Trial Balance Integration for eBalance
Extracts trial balance data for MOF reporting
"""

import frappe
from frappe import _
from frappe.utils import flt


def get_trial_balance_for_ebalance(company, from_date, to_date, filters=None):
    """
    Get trial balance data formatted for eBalance submission

    Args:
        company: Company name
        from_date: Period start date
        to_date: Period end date
        filters: Additional filters

    Returns:
        dict: Trial balance data in eBalance format
    """
    from erpnext.accounts.report.trial_balance.trial_balance import execute

    # Prepare filters for trial balance report
    report_filters = frappe._dict({
        "company": company,
        "from_date": from_date,
        "to_date": to_date,
        "with_period_closing_entry": 1,
        "show_unclosed_fy_pl_balances": 0
    })

    if filters:
        report_filters.update(filters)

    # Execute trial balance report
    columns, data = execute(report_filters)

    # Transform to eBalance format
    return _transform_to_ebalance_format(data, from_date, to_date)


def _transform_to_ebalance_format(trial_balance_data, from_date, to_date):
    """
    Transform ERPNext trial balance to eBalance format

    Args:
        trial_balance_data: Trial balance report data
        from_date: Period start date
        to_date: Period end date

    Returns:
        dict: eBalance formatted data
    """
    result = {
        "period_start": str(from_date),
        "period_end": str(to_date),
        "accounts": [],
        "totals": {
            "opening_debit": 0,
            "opening_credit": 0,
            "debit": 0,
            "credit": 0,
            "closing_debit": 0,
            "closing_credit": 0
        }
    }

    for row in trial_balance_data or []:
        if not row.get("account"):
            continue

        # Skip group accounts (totals)
        if row.get("is_group"):
            continue

        account_data = {
            "account": row.get("account", ""),
            "account_number": _extract_account_number(row.get("account", "")),
            "account_name": row.get("account_name", row.get("account", "")),
            "opening_debit": flt(row.get("opening_debit", 0), 2),
            "opening_credit": flt(row.get("opening_credit", 0), 2),
            "debit": flt(row.get("debit", 0), 2),
            "credit": flt(row.get("credit", 0), 2),
            "closing_debit": flt(row.get("closing_debit", 0), 2),
            "closing_credit": flt(row.get("closing_credit", 0), 2)
        }

        result["accounts"].append(account_data)

        # Update totals
        for key in ["opening_debit", "opening_credit", "debit", "credit", "closing_debit", "closing_credit"]:
            result["totals"][key] += account_data[key]

    # Round totals
    for key in result["totals"]:
        result["totals"][key] = flt(result["totals"][key], 2)

    return result


def _extract_account_number(account_name):
    """
    Extract account number from account name

    Args:
        account_name: Full account name (e.g., "1100 - Cash - Company")

    Returns:
        str: Account number or empty string
    """
    if not account_name:
        return ""

    # Try to extract number from beginning
    parts = account_name.split(" - ")
    if parts and parts[0].replace(".", "").isdigit():
        return parts[0]

    return ""


def get_balance_sheet_data(company, as_on_date):
    """
    Get balance sheet data for eBalance

    Args:
        company: Company name
        as_on_date: Balance sheet date

    Returns:
        dict: Balance sheet in eBalance format
    """
    from erpnext.accounts.report.balance_sheet.balance_sheet import execute

    filters = frappe._dict({
        "company": company,
        "filter_based_on": "Date Range",
        "period_start_date": frappe.db.get_value(
            "Fiscal Year",
            {"disabled": 0},
            "year_start_date"
        ),
        "period_end_date": as_on_date,
        "periodicity": "Yearly",
        "accumulated_values": 1
    })

    result = execute(filters)
    _columns, data = result[0], result[1]

    return _transform_balance_sheet(data)


def _transform_balance_sheet(balance_sheet_data):
    """
    Transform balance sheet to eBalance format

    Args:
        balance_sheet_data: Balance sheet report data

    Returns:
        dict: eBalance formatted balance sheet
    """
    result = {
        "assets": [],
        "liabilities": [],
        "equity": [],
        "totals": {
            "total_assets": 0,
            "total_liabilities": 0,
            "total_equity": 0
        }
    }

    current_section = None

    for row in balance_sheet_data or []:
        account = row.get("account", "")

        # Detect section
        if "Asset" in account:
            current_section = "assets"
        elif "Liability" in account:
            current_section = "liabilities"
        elif "Equity" in account:
            current_section = "equity"

        if current_section and not row.get("is_group"):
            item = {
                "account": account,
                "balance": flt(row.get("value", 0), 2)
            }
            result[current_section].append(item)

    # Calculate totals
    result["totals"]["total_assets"] = sum(
        item["balance"] for item in result["assets"]
    )
    result["totals"]["total_liabilities"] = sum(
        item["balance"] for item in result["liabilities"]
    )
    result["totals"]["total_equity"] = sum(
        item["balance"] for item in result["equity"]
    )

    return result


def get_profit_loss_data(company, from_date, to_date):
    """
    Get profit and loss data for eBalance

    Args:
        company: Company name
        from_date: Period start
        to_date: Period end

    Returns:
        dict: P&L in eBalance format
    """
    from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

    filters = frappe._dict({
        "company": company,
        "filter_based_on": "Date Range",
        "period_start_date": from_date,
        "period_end_date": to_date,
        "periodicity": "Monthly",
        "accumulated_values": 0
    })

    result = execute(filters)
    _columns, data = result[0], result[1]

    return _transform_profit_loss(data, from_date, to_date)


def _transform_profit_loss(pl_data, from_date, to_date):
    """
    Transform P&L to eBalance format

    Args:
        pl_data: P&L report data
        from_date: Period start
        to_date: Period end

    Returns:
        dict: eBalance formatted P&L
    """
    result = {
        "period_start": str(from_date),
        "period_end": str(to_date),
        "income": [],
        "expenses": [],
        "totals": {
            "total_income": 0,
            "total_expenses": 0,
            "net_profit": 0
        }
    }

    current_section = None

    for row in pl_data or []:
        account = row.get("account", "")

        # Detect section
        if "Income" in account or "Revenue" in account:
            current_section = "income"
        elif "Expense" in account:
            current_section = "expenses"

        if current_section and not row.get("is_group"):
            item = {
                "account": account,
                "amount": flt(row.get("value", 0), 2)
            }
            result[current_section].append(item)

    # Calculate totals
    result["totals"]["total_income"] = sum(
        item["amount"] for item in result["income"]
    )
    result["totals"]["total_expenses"] = sum(
        item["amount"] for item in result["expenses"]
    )
    result["totals"]["net_profit"] = (
        result["totals"]["total_income"] - result["totals"]["total_expenses"]
    )

    return result


@frappe.whitelist()
def preview_ebalance_data(company, from_date, to_date, report_type="trial_balance"):
    """
    Preview eBalance data before submission

    Args:
        company: Company name
        from_date: Period start
        to_date: Period end
        report_type: Type of report (trial_balance, balance_sheet, profit_loss)

    Returns:
        dict: Preview data
    """
    frappe.has_permission("eBalance Settings", throw=True)

    if report_type == "trial_balance":
        return get_trial_balance_for_ebalance(company, from_date, to_date)
    elif report_type == "balance_sheet":
        return get_balance_sheet_data(company, to_date)
    elif report_type == "profit_loss":
        return get_profit_loss_data(company, from_date, to_date)
    else:
        frappe.throw(_("Invalid report type: {0}").format(report_type))
