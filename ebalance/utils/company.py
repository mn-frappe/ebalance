# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
Company Integration Utilities for eBalance

For multi-company support, use:

    from ebalance.mn_entity import get_entity_for_doc, get_entity_for_company

    # From a document (preferred - ensures all apps use same entity)
    entity = get_entity_for_doc(journal_entry)
    org_regno = entity.org_regno

    # From company name
    entity = get_entity_for_company("ABC LLC")
"""

import frappe
from typing import Optional

# Re-export from mn_entity for convenience
from ebalance.mn_entity import (
    get_entity_for_doc,
    get_entity_for_company,
    get_default_company,
    MNEntity,
)

__all__ = [
    "get_entity_for_doc",
    "get_entity_for_company",
    "get_default_company",
    "MNEntity",
    # Legacy functions
    "get_ebalance_company_info",
    "get_org_regno",
]


# =============================================================================
# Legacy functions (for backward compatibility)
# =============================================================================

def get_ebalance_company_info(settings=None, company: Optional[str] = None, doc=None) -> dict:
    """
    DEPRECATED: Use get_entity_for_doc() instead.
    
    Get company info for eBalance. Priority:
    1. doc (if provided) - uses doc.company
    2. company (if provided) - uses directly
    3. settings.company (if settings has company link)
    """
    if settings is None:
        settings = frappe.get_single("eBalance Settings")
    
    # Determine company
    company_name = None
    
    if doc and hasattr(doc, "company"):
        company_name = doc.company
    elif company:
        company_name = company
    elif settings and hasattr(settings, "company"):
        company_name = settings.company  # type: ignore
    
    result = {
        "org_regno": None,
        "org_id": None,
        "company": None,
        "source": "settings"
    }
    
    # If we have a company, use the new method
    if company_name:
        try:
            entity = get_entity_for_company(company_name)
            return {
                "org_regno": entity.org_regno,
                "org_id": entity.ent_id,  # eBalance uses org_id
                "company": entity.company,
                "source": "company"
            }
        except Exception:
            pass
    
    # Fall back to settings fields
    if settings:
        result["org_regno"] = getattr(settings, "org_regno", None)
        result["org_id"] = getattr(settings, "org_id", None)
    
    return result


def get_org_regno(settings=None, company: Optional[str] = None, doc=None) -> Optional[str]:
    """Get organization registry number (PIN)."""
    return get_ebalance_company_info(settings, company, doc).get("org_regno")
