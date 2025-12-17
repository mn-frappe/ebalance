# -*- coding: utf-8 -*-
# Copyright (c) 2025, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Account Integration for eBalance

Handles Account DocType events to maintain MOF account mapping suggestions.
When an Account is created or updated, this module can suggest MOF standard
account mappings based on the account name and type.
"""


import frappe


def on_update(doc, method=None):
    """
    Called when an Account is updated.

    Can be used to:
    - Suggest MOF account mappings
    - Update cached account lists
    - Validate account compatibility with MOF reporting
    """
    # Only process if eBalance is enabled
    try:
        settings = frappe.get_single("eBalance Settings")
        if not getattr(settings, "enabled", False):
            return
    except Exception:
        return

    # Clear any cached account lists
    cache_key = f"ebalance_accounts_{doc.company}"
    frappe.cache().delete_value(cache_key)


def suggest_mof_mapping(account_name: str, account_type: str | None = None) -> str | None:
    """
    Suggest a MOF account mapping based on account name and type.

    Args:
        account_name: ERPNext account name
        account_type: ERPNext account type (Asset, Liability, Income, Expense)

    Returns:
        MOF account number suggestion or None
    """
    # Basic mapping suggestions based on account type
    # This is a simplified version - full implementation would use NLP/fuzzy matching

    type_prefixes = {
        "Asset": "1",      # MOF assets start with 1
        "Liability": "2",  # MOF liabilities start with 2
        "Equity": "3",     # MOF equity starts with 3
        "Income": "5",     # MOF income starts with 5
        "Expense": "6",    # MOF expenses start with 6
    }

    if account_type and account_type in type_prefixes:
        prefix = type_prefixes[account_type]

        # Find MOF accounts starting with this prefix
        mof_accounts = frappe.get_all(
            "MOF Account Mapping",
            filters={"mof_account_number": ["like", f"{prefix}%"]},
            fields=["mof_account_number", "mof_account_name_mn", "mof_account_name_en"],
            limit=10
        )

        if mof_accounts:
            # Return first match (simplified - would use better matching in production)
            return mof_accounts[0].mof_account_number

    return None
