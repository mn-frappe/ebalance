# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBalance Performance Utilities

Provides incremental GL aggregation, caching, and performance optimizations
for high-volume financial reporting operations.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_first_day, get_last_day
from typing import Optional, List, Dict, Any
import time
import functools


# =============================================================================
# Performance Indexes
# =============================================================================

EBALANCE_INDEXES = [
    # MOF Account Mapping indexes
    {
        "table": "tabMOF Account Mapping",
        "columns": ["mof_account_number"],
        "name": "idx_mof_account_number"
    },
    {
        "table": "tabMOF Account Mapping",
        "columns": ["company"],
        "name": "idx_mof_company"
    },
    # eBalance Submission Log
    {
        "table": "tabeBalance Submission Log",
        "columns": ["company", "period", "status"],
        "name": "idx_ebalance_submission"
    },
    # eBalance Report Period
    {
        "table": "tabeBalance Report Period",
        "columns": ["company", "status"],
        "name": "idx_ebalance_period"
    },
    # Materialized balance cache
    {
        "table": "tabeBalance Account Cache",
        "columns": ["company", "account", "fiscal_year", "month"],
        "name": "idx_ebalance_cache"
    },
]


def ensure_indexes():
    """Create performance indexes if they don't exist."""
    for idx in EBALANCE_INDEXES:
        try:
            index_name = idx["name"]
            table = idx["table"]
            columns = ", ".join([f"`{c}`" for c in idx["columns"]])
            
            # Check if index exists
            existing = frappe.db.sql(f"""
                SHOW INDEX FROM `{table}` WHERE Key_name = %s
            """, (index_name,))
            
            if not existing:
                frappe.db.sql(f"""
                    CREATE INDEX `{index_name}` ON `{table}` ({columns})
                """)
                frappe.logger("ebalance").info(f"Created index {index_name} on {table}")
        except Exception as e:
            frappe.logger("ebalance").debug(f"Could not create index {idx['name']}: {e}")


# =============================================================================
# Caching Utilities
# =============================================================================

def cache_key(prefix: str, *args) -> str:
    """Generate a cache key."""
    return f"ebalance:{prefix}:" + ":".join(str(a) for a in args)


def get_cached(key: str):
    """Get value from cache."""
    return frappe.cache().get_value(key)


def set_cached(key: str, value: Any, ttl: int = 3600):
    """Set value in cache with TTL."""
    frappe.cache().set_value(key, value, expires_in_sec=ttl)


def invalidate_cache(pattern: str):
    """Invalidate cache keys matching pattern."""
    # Redis pattern matching
    frappe.cache().delete_keys(f"ebalance:{pattern}*")


# =============================================================================
# Incremental GL Aggregation
# =============================================================================

def get_monthly_balance_cached(
    company: str,
    account: str,
    fiscal_year: str,
    month: int
) -> Dict[str, float]:
    """
    Get monthly account balance from cache or calculate.
    
    Returns:
        dict with opening_debit, opening_credit, debit, credit, closing_debit, closing_credit
    """
    key = cache_key("monthly_balance", company, account, fiscal_year, month)
    cached = get_cached(key)
    
    if cached:
        return cached
    
    # Calculate and cache
    balance = calculate_monthly_balance(company, account, fiscal_year, month)
    set_cached(key, balance, ttl=86400)  # Cache for 24 hours
    
    return balance


def calculate_monthly_balance(
    company: str,
    account: str,
    fiscal_year: str,
    month: int
) -> Dict[str, float]:
    """
    Calculate monthly balance for an account.
    Uses optimized query with GL Entry indexes.
    """
    from frappe.utils import get_first_day, get_last_day, getdate
    
    # Get fiscal year dates
    fy = frappe.get_doc("Fiscal Year", fiscal_year)
    year_start = getdate(fy.year_start_date)
    
    # Calculate month dates
    month_start = get_first_day(f"{year_start.year if month >= year_start.month else year_start.year + 1}-{month:02d}-01")
    month_end = get_last_day(month_start)
    
    # Get opening balance (before month start)
    opening = frappe.db.sql("""
        SELECT 
            COALESCE(SUM(debit), 0) as debit,
            COALESCE(SUM(credit), 0) as credit
        FROM `tabGL Entry`
        WHERE company = %s
        AND account = %s
        AND posting_date < %s
        AND is_cancelled = 0
    """, (company, account, month_start), as_dict=True)[0]
    
    # Get month transactions
    month_txn = frappe.db.sql("""
        SELECT 
            COALESCE(SUM(debit), 0) as debit,
            COALESCE(SUM(credit), 0) as credit
        FROM `tabGL Entry`
        WHERE company = %s
        AND account = %s
        AND posting_date BETWEEN %s AND %s
        AND is_cancelled = 0
    """, (company, account, month_start, month_end), as_dict=True)[0]
    
    opening_debit = flt(opening.debit)
    opening_credit = flt(opening.credit)
    debit = flt(month_txn.debit)
    credit = flt(month_txn.credit)
    
    return {
        "opening_debit": opening_debit,
        "opening_credit": opening_credit,
        "debit": debit,
        "credit": credit,
        "closing_debit": opening_debit + debit,
        "closing_credit": opening_credit + credit,
    }


def recalculate_period_cache(company: str, fiscal_year: str, from_month: int = 1):
    """
    Recalculate cached balances from a specific month onwards.
    Called when GL entries are modified.
    """
    # Get all accounts for company
    accounts = frappe.get_all(
        "Account",
        filters={"company": company, "is_group": 0},
        pluck="name"
    )
    
    # Invalidate and recalculate
    for account in accounts:
        for month in range(from_month, 13):
            key = cache_key("monthly_balance", company, account, fiscal_year, month)
            frappe.cache().delete_value(key)
            # Recalculate will happen on next access


# =============================================================================
# Trial Balance Aggregation
# =============================================================================

def get_trial_balance_fast(
    company: str,
    fiscal_year: str,
    month: int,
    use_cache: bool = True
) -> List[Dict]:
    """
    Get trial balance with optimized caching.
    Returns list of accounts with balances.
    """
    key = cache_key("trial_balance", company, fiscal_year, month)
    
    if use_cache:
        cached = get_cached(key)
        if cached:
            return cached
    
    # Get all accounts with MOF mapping
    accounts = frappe.db.sql("""
        SELECT 
            a.name as account,
            a.account_type,
            a.root_type,
            m.mof_account_number,
            m.mof_account_name_mn
        FROM `tabAccount` a
        LEFT JOIN `tabMOF Account Mapping Item` mi ON mi.erpnext_account = a.name
        LEFT JOIN `tabMOF Account Mapping` m ON m.name = mi.parent
        WHERE a.company = %s
        AND a.is_group = 0
        ORDER BY a.name
    """, (company,), as_dict=True)
    
    result = []
    for acc in accounts:
        balance = get_monthly_balance_cached(company, acc.account, fiscal_year, month)
        result.append({
            **acc,
            **balance
        })
    
    if use_cache:
        set_cached(key, result, ttl=3600)
    
    return result


# =============================================================================
# MOF Report Generation
# =============================================================================

def generate_mof_report_data(
    company: str,
    fiscal_year: str,
    month: int,
    report_type: str = "BS01"
) -> Dict:
    """
    Generate MOF report data with caching.
    
    Args:
        company: Company name
        fiscal_year: Fiscal year
        month: Month number (1-12)
        report_type: MOF report type (BS01, IS01, etc.)
    """
    key = cache_key("mof_report", company, fiscal_year, month, report_type)
    cached = get_cached(key)
    
    if cached:
        return cached
    
    # Get trial balance
    trial_balance = get_trial_balance_fast(company, fiscal_year, month)
    
    # Aggregate by MOF account
    mof_totals = {}
    for acc in trial_balance:
        mof_code = acc.get("mof_account_number")
        if not mof_code:
            continue
        
        if mof_code not in mof_totals:
            mof_totals[mof_code] = {
                "mof_account_number": mof_code,
                "mof_account_name_mn": acc.get("mof_account_name_mn"),
                "opening_debit": 0,
                "opening_credit": 0,
                "debit": 0,
                "credit": 0,
                "closing_debit": 0,
                "closing_credit": 0,
            }
        
        for field in ["opening_debit", "opening_credit", "debit", "credit", "closing_debit", "closing_credit"]:
            mof_totals[mof_code][field] += flt(acc.get(field, 0))
    
    result = {
        "company": company,
        "fiscal_year": fiscal_year,
        "month": month,
        "report_type": report_type,
        "rows": list(mof_totals.values())
    }
    
    set_cached(key, result, ttl=3600)
    return result


# =============================================================================
# Auto-Sync Report Periods (Autopilot)
# =============================================================================

def auto_sync_report_periods():
    """
    Automatically sync report periods from eBalance API.
    Called by scheduler based on autopilot settings.
    """
    settings = frappe.get_single("eBalance Settings")
    if not getattr(settings, "auto_sync_periods", False):
        return
    
    try:
        from ebalance.api.client import EBalanceClient
        client = EBalanceClient()
        
        # Fetch periods from API
        periods = client.get_report_periods() if hasattr(client, "get_report_periods") else []
        
        # Update local records
        for period in periods:
            frappe.enqueue(
                "ebalance.setup.sync.sync_report_period",
                period_data=period,
                queue="short"
            )
            
    except Exception as e:
        frappe.log_error(f"Auto-sync report periods failed: {e}")


def auto_submit_reports():
    """
    Automatically submit due reports.
    Called by scheduler based on autopilot settings.
    """
    settings = frappe.get_single("eBalance Settings")
    if not getattr(settings, "auto_fetch_forms", False):
        return
    
    # Find reports due for submission
    due_reports = frappe.get_all(
        "eBalance Report Period",
        filters={
            "status": "Draft",
            "end_date": ["<=", frappe.utils.today()]
        },
        fields=["name", "company", "period_name"],
        limit=10
    )
    
    for report in due_reports:
        frappe.enqueue(
            "ebalance.api.client.submit_report",
            report_name=report.name,
            queue="long",
            timeout=600
        )


# =============================================================================
# GL Entry Hook for Cache Invalidation
# =============================================================================

def on_gl_entry_update(doc, method=None):
    """
    Invalidate cache when GL Entry is created/modified.
    """
    if not doc.company or not doc.account:
        return
    
    # Get fiscal year for the posting date
    fiscal_year = frappe.get_value(
        "Fiscal Year",
        {"year_start_date": ["<=", doc.posting_date], "year_end_date": [">=", doc.posting_date]},
        "name"
    )
    
    if fiscal_year:
        month = getdate(doc.posting_date).month
        
        # Invalidate this account's cache for this month and onwards
        for m in range(month, 13):
            key = cache_key("monthly_balance", doc.company, doc.account, fiscal_year, m)
            frappe.cache().delete_value(key)
        
        # Invalidate trial balance cache
        for m in range(month, 13):
            key = cache_key("trial_balance", doc.company, fiscal_year, m)
            frappe.cache().delete_value(key)


# =============================================================================
# Performance Monitoring
# =============================================================================

def track_api_performance(method: str):
    """Decorator to track API call performance."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            success = True
            try:
                return func(*args, **kwargs)
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start
                try:
                    frappe.cache().hincrby("ebalance:api_stats", f"{method}:calls", 1)
                    frappe.cache().hincrbyfloat("ebalance:api_stats", f"{method}:time", duration)
                    if not success:
                        frappe.cache().hincrby("ebalance:api_stats", f"{method}:errors", 1)
                except Exception:
                    pass
        return wrapper
    return decorator
