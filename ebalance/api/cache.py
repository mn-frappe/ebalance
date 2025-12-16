# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
eBalance Caching Layer

High-performance Redis caching for:
- MOF Account Mappings (154 accounts)
- API Tokens
- Report Periods
- GL Balances (short-lived)

Cache Strategy:
- MOF Accounts: 24 hours (rarely changes)
- Tokens: Until expiry
- Periods: 1 hour
- Balances: 5 minutes (during report generation)
"""

import json
import frappe
from frappe.utils import cint, flt
from functools import wraps
from typing import Any, Optional, Callable
from datetime import timedelta


# Cache key prefixes
CACHE_PREFIX = "ebalance:"
CACHE_KEYS = {
	"mof_accounts": f"{CACHE_PREFIX}mof_accounts",
	"mof_account": f"{CACHE_PREFIX}mof_account:",  # + mof_code
	"mof_mapping_lookup": f"{CACHE_PREFIX}mof_lookup",  # account_name -> mof_code
	"token": f"{CACHE_PREFIX}token",
	"periods": f"{CACHE_PREFIX}periods:",  # + environment
	"balance": f"{CACHE_PREFIX}balance:",  # + company:date_range:mof_code
	"gl_totals": f"{CACHE_PREFIX}gl_totals:",  # + company:date_range
	"account_list": f"{CACHE_PREFIX}accounts:",  # + company
	"keywords": f"{CACHE_PREFIX}keywords",  # Precompiled keyword patterns
}

# Cache TTLs in seconds
CACHE_TTL = {
	"mof_accounts": 86400,  # 24 hours
	"mof_account": 86400,
	"mof_mapping_lookup": 86400,
	"token": 3600,  # 1 hour (tokens usually expire in 1h)
	"periods": 3600,  # 1 hour
	"balance": 300,  # 5 minutes
	"gl_totals": 300,
	"account_list": 600,  # 10 minutes
	"keywords": 86400,
}


def get_cache():
	"""Get Frappe cache instance"""
	return frappe.cache()


def cache_key(prefix: str, *args) -> str:
	"""Build cache key from prefix and arguments"""
	if args:
		suffix = ":".join(str(a) for a in args if a)
		return f"{prefix}{suffix}"
	return prefix


def cache_get(key: str) -> Optional[Any]:
	"""Get value from cache"""
	try:
		value = get_cache().get_value(key)
		if value:
			if isinstance(value, (str, bytes)):
				try:
					return json.loads(value)
				except (json.JSONDecodeError, TypeError):
					return value
			return value
	except Exception:
		pass
	return None


def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
	"""Set value in cache with TTL"""
	try:
		if isinstance(value, (dict, list)):
			value = json.dumps(value, default=str)
		get_cache().set_value(key, value, expires_in_sec=ttl)
		return True
	except Exception:
		return False


def cache_delete(key: str) -> bool:
	"""Delete key from cache"""
	try:
		get_cache().delete_value(key)
		return True
	except Exception:
		return False


def cache_delete_pattern(pattern: str) -> int:
	"""Delete all keys matching pattern"""
	count = 0
	try:
		cache = get_cache()
		# Frappe doesn't have native pattern delete, use heuristic
		for suffix in ["", "*"]:
			cache.delete_value(f"{pattern}{suffix}")
			count += 1
	except Exception:
		pass
	return count


def cached(key_prefix: str, ttl: int = 300, key_func: Callable = None):
	"""
	Decorator to cache function results.
	
	Args:
		key_prefix: Cache key prefix
		ttl: Time to live in seconds
		key_func: Function to generate cache key from args
	
	Usage:
		@cached("mof_balance", ttl=300, key_func=lambda c,d1,d2,m: f"{c}:{d1}:{d2}:{m}")
		def get_mof_balance(company, from_date, to_date, mof_code):
			...
	"""
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			# Generate cache key
			if key_func:
				key_suffix = key_func(*args, **kwargs)
			else:
				key_suffix = ":".join(str(a) for a in args)
			
			full_key = cache_key(key_prefix, key_suffix)
			
			# Try cache first
			cached_value = cache_get(full_key)
			if cached_value is not None:
				return cached_value
			
			# Call function
			result = func(*args, **kwargs)
			
			# Store in cache
			if result is not None:
				cache_set(full_key, result, ttl)
			
			return result
		return wrapper
	return decorator


# =============================================================================
# MOF Account Cache Functions
# =============================================================================

def get_all_mof_accounts(force_refresh: bool = False) -> list:
	"""
	Get all MOF accounts from cache or database.
	
	Returns:
		list: List of MOF account dicts
	"""
	if not force_refresh:
		cached = cache_get(CACHE_KEYS["mof_accounts"])
		if cached:
			return cached
	
	# Fetch from database with single query
	accounts = frappe.get_all(
		"MOF Account Mapping",
		filters={"enabled": 1},
		fields=[
			"name", "mof_account_number", "mof_account_name",
			"mof_account_name_mn", "is_group", "parent_mof_account",
			"root_type", "balance_must_be"
		],
		order_by="mof_account_number"
	)
	
	# Cache result
	cache_set(CACHE_KEYS["mof_accounts"], accounts, CACHE_TTL["mof_accounts"])
	
	return accounts


def get_mof_account(mof_code: str, force_refresh: bool = False) -> Optional[dict]:
	"""
	Get single MOF account with linked ERPNext accounts.
	
	Args:
		mof_code: MOF account number
		
	Returns:
		dict: MOF account with accounts list
	"""
	key = cache_key(CACHE_KEYS["mof_account"], mof_code)
	
	if not force_refresh:
		cached = cache_get(key)
		if cached:
			return cached
	
	# Get MOF account
	if not frappe.db.exists("MOF Account Mapping", mof_code):
		return None
	
	doc = frappe.get_doc("MOF Account Mapping", mof_code)
	
	result = {
		"mof_code": doc.mof_account_number,
		"name_en": doc.mof_account_name,
		"name_mn": doc.mof_account_name_mn,
		"is_group": doc.is_group,
		"root_type": doc.root_type,
		"accounts": [row.account for row in doc.accounts] if hasattr(doc, "accounts") else []
	}
	
	cache_set(key, result, CACHE_TTL["mof_account"])
	
	return result


def get_mof_mapping_lookup(force_refresh: bool = False) -> dict:
	"""
	Get ERPNext account -> MOF code lookup dictionary.
	
	Returns:
		dict: {account_name: mof_code}
	"""
	if not force_refresh:
		cached = cache_get(CACHE_KEYS["mof_mapping_lookup"])
		if cached:
			return cached
	
	# Build lookup with single query on child table
	lookup = {}
	
	items = frappe.get_all(
		"MOF Account Mapping Item",
		fields=["parent", "account"],
	)
	
	for item in items:
		lookup[item.account] = item.parent
	
	cache_set(CACHE_KEYS["mof_mapping_lookup"], lookup, CACHE_TTL["mof_mapping_lookup"])
	
	return lookup


def invalidate_mof_cache():
	"""Invalidate all MOF account caches"""
	cache_delete(CACHE_KEYS["mof_accounts"])
	cache_delete(CACHE_KEYS["mof_mapping_lookup"])
	cache_delete_pattern(CACHE_KEYS["mof_account"])


# =============================================================================
# GL Balance Cache Functions  
# =============================================================================

def get_cached_gl_totals(company: str, from_date: str, to_date: str, force_refresh: bool = False) -> Optional[dict]:
	"""
	Get cached GL totals for a date range.
	
	Returns:
		dict: {account_name: {"debit": x, "credit": y}}
	"""
	key = cache_key(CACHE_KEYS["gl_totals"], company, str(from_date), str(to_date))
	
	if not force_refresh:
		cached = cache_get(key)
		if cached:
			return cached
	
	return None


def set_cached_gl_totals(company: str, from_date: str, to_date: str, totals: dict):
	"""Cache GL totals"""
	key = cache_key(CACHE_KEYS["gl_totals"], company, str(from_date), str(to_date))
	cache_set(key, totals, CACHE_TTL["gl_totals"])


def invalidate_balance_cache(company: str = None):
	"""Invalidate balance caches, optionally for specific company"""
	if company:
		cache_delete_pattern(f"{CACHE_KEYS['balance']}{company}")
		cache_delete_pattern(f"{CACHE_KEYS['gl_totals']}{company}")
	else:
		cache_delete_pattern(CACHE_KEYS["balance"])
		cache_delete_pattern(CACHE_KEYS["gl_totals"])


# =============================================================================
# Token Cache Functions
# =============================================================================

def get_cached_token() -> Optional[dict]:
	"""Get cached token with expiry"""
	return cache_get(CACHE_KEYS["token"])


def set_cached_token(token: str, expires_in: int):
	"""Cache token with TTL"""
	data = {"token": token, "expires_in": expires_in}
	# Cache for slightly less than expiry to ensure refresh before expiry
	ttl = max(expires_in - 60, 60)
	cache_set(CACHE_KEYS["token"], data, ttl)


def invalidate_token_cache():
	"""Invalidate token cache"""
	cache_delete(CACHE_KEYS["token"])


# =============================================================================
# Period Cache Functions
# =============================================================================

def get_cached_periods(environment: str = "Staging") -> Optional[list]:
	"""Get cached report periods"""
	key = cache_key(CACHE_KEYS["periods"], environment)
	return cache_get(key)


def set_cached_periods(environment: str, periods: list):
	"""Cache report periods"""
	key = cache_key(CACHE_KEYS["periods"], environment)
	cache_set(key, periods, CACHE_TTL["periods"])


# =============================================================================
# Account List Cache
# =============================================================================

def get_cached_accounts(company: str, filters: dict = None) -> Optional[list]:
	"""Get cached account list for company"""
	filter_hash = hash(json.dumps(filters, sort_keys=True, default=str)) if filters else ""
	key = cache_key(CACHE_KEYS["account_list"], company, filter_hash)
	return cache_get(key)


def set_cached_accounts(company: str, accounts: list, filters: dict = None):
	"""Cache account list"""
	filter_hash = hash(json.dumps(filters, sort_keys=True, default=str)) if filters else ""
	key = cache_key(CACHE_KEYS["account_list"], company, filter_hash)
	cache_set(key, accounts, CACHE_TTL["account_list"])


# =============================================================================
# Cache Hooks for DocType Events
# =============================================================================

def on_mof_account_update(doc, method=None):
	"""Hook: Called when MOF Account Mapping is saved"""
	invalidate_mof_cache()


def on_gl_entry_update(doc, method=None):
	"""Hook: Called when GL Entry is posted"""
	invalidate_balance_cache(doc.company)


def on_account_update(doc, method=None):
	"""Hook: Called when Account is saved"""
	cache_delete_pattern(f"{CACHE_KEYS['account_list']}{doc.company}")
