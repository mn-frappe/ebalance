# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportIndexIssue=false

"""
Jinja template utilities for eBalance
Custom filters and functions for report templates
"""

import frappe
from frappe.utils import flt, fmt_money, formatdate, getdate


def get_jinja_env():
    """
    Get Jinja environment with eBalance filters

    Returns:
        dict: Jinja environment methods
    """
    return {
        "format_mnt": format_mnt,
        "format_ebalance_date": format_ebalance_date,
        "get_account_balance": get_account_balance,
        "get_period_status": get_period_status,
        "get_submission_status_badge": get_submission_status_badge,
        "get_ebalance_settings": get_ebalance_settings
    }


def format_mnt(amount, precision=2):
    """
    Format amount in Mongolian Tugrik

    Args:
        amount: Numeric amount
        precision: Decimal precision (default 2)

    Returns:
        str: Formatted amount with MNT symbol
    """
    if amount is None:
        return "₮0.00"

    formatted = fmt_money(flt(amount, precision), currency="MNT")
    return formatted or f"₮{flt(amount, precision):,.2f}"


def format_ebalance_date(date_value, format_str=None):
    """
    Format date for eBalance display

    Args:
        date_value: Date value
        format_str: Custom format string (optional)

    Returns:
        str: Formatted date
    """
    if not date_value:
        return ""

    date_obj = getdate(date_value)

    if format_str:
        return date_obj.strftime(format_str)

    # Default Mongolian date format: YYYY оны MM сарын DD
    return formatdate(date_obj, "yyyy-MM-dd")


def get_account_balance(account, company=None, as_on_date=None):
    """
    Get account balance for Jinja templates

    Args:
        account: Account name
        company: Company name (optional)
        as_on_date: Balance date (optional)

    Returns:
        float: Account balance
    """
    filters = {"account": account, "is_cancelled": 0}

    if company:
        filters["company"] = company

    if as_on_date:
        filters["posting_date"] = ["<=", as_on_date]

    balance = frappe.db.sql("""
        SELECT SUM(debit) - SUM(credit) as balance
        FROM `tabGL Entry`
        WHERE account = %(account)s
        AND is_cancelled = 0
        {company_filter}
        {date_filter}
    """.format(
        company_filter="AND company = %(company)s" if company else "",
        date_filter="AND posting_date <= %(as_on_date)s" if as_on_date else ""
    ), {
        "account": account,
        "company": company,
        "as_on_date": as_on_date
    }, as_dict=True)

    return flt(balance[0].balance if balance else 0, 2)


def get_period_status(period_name):
    """
    Get period status with color indicator

    Args:
        period_name: Period name

    Returns:
        dict: Status with indicator color
    """
    period = frappe.db.get_value(
        "eBalance Report Period",
        {"period_name": period_name},
        ["status", "deadline"],
        as_dict=True
    )

    if not period:
        return {"status": "Not Found", "indicator": "grey"}

    status_colors = {
        "Active": "green",
        "Closed": "blue",
        "Expired": "red",
        "Draft": "orange"
    }

    return {
        "status": period.status,
        "indicator": status_colors.get(period.status, "grey"),
        "deadline": period.deadline
    }


def get_submission_status_badge(status):
    """
    Get HTML badge for submission status

    Args:
        status: Submission status

    Returns:
        str: HTML badge markup
    """
    status_config = {
        "Draft": ("grey", "📝"),
        "In Progress": ("yellow", "⏳"),
        "Pending": ("orange", "🔄"),
        "Submitted": ("green", "✅"),
        "Confirmed": ("blue", "✓"),
        "Error": ("red", "❌"),
        "Rejected": ("red", "⚠️")
    }

    color, icon = status_config.get(status, ("grey", "?"))

    return f'<span class="indicator-pill {color}">{icon} {status}</span>'


def get_ebalance_settings():
    """
    Get eBalance settings for templates

    Returns:
        dict: Safe settings (excludes credentials)
    """
    try:
        settings = frappe.get_cached_doc("eBalance Settings")

        return {
            "enabled": settings.enabled,
            "environment": settings.environment,
            "org_reg_no": settings.org_reg_no,
            "auto_sync_periods": settings.auto_sync_periods,
            "auto_sync_interval": settings.auto_sync_interval
        }
    except Exception:
        return {
            "enabled": False,
            "environment": "Staging"
        }


# Filters for Jinja environment
def ebalance_filters():
    """
    Return dict of filters for Jinja

    Returns:
        dict: Filter functions
    """
    return {
        "format_mnt": format_mnt,
        "ebalance_date": format_ebalance_date,
        "status_badge": get_submission_status_badge
    }


# Global functions for Jinja
def ebalance_globals():
    """
    Return dict of global functions for Jinja

    Returns:
        dict: Global functions
    """
    return {
        "get_account_balance": get_account_balance,
        "get_period_status": get_period_status,
        "get_ebalance_settings": get_ebalance_settings
    }
