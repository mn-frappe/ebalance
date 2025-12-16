# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOperatorIssue=false

"""
eBalance Database Indexes

Performance-critical indexes for eBalance queries.
Run after install to ensure optimal query performance.

Usage:
    bench --site [sitename] execute ebalance.setup.indexes.create_indexes
"""

import frappe


# Index definitions: (table, column(s), index_name, unique)
INDEXES = [
	# MOF Account Mapping - fast lookups by account number
	("tabMOF Account Mapping", "mof_account_number", "idx_mof_account_number", False),
	("tabMOF Account Mapping", "enabled", "idx_mof_enabled", False),
	("tabMOF Account Mapping", "is_group", "idx_mof_is_group", False),
	("tabMOF Account Mapping", "root_type", "idx_mof_root_type", False),
	
	# MOF Account Mapping Item - fast account->mof lookup
	("tabMOF Account Mapping Item", "account", "idx_mof_item_account", False),
	("tabMOF Account Mapping Item", "parent", "idx_mof_item_parent", False),
	
	# eBalance Report Request - fast status queries
	("tabeBalance Report Request", "status", "idx_ebalance_req_status", False),
	("tabeBalance Report Request", "company", "idx_ebalance_req_company", False),
	("tabeBalance Report Request", "fiscal_year", "idx_ebalance_req_fy", False),
	
	# eBalance Submission Log - audit queries
	("tabeBalance Submission Log", "report_request", "idx_submission_req", False),
	("tabeBalance Submission Log", "status", "idx_submission_status", False),
	("tabeBalance Submission Log", "creation", "idx_submission_creation", False),
	
	# eBalance Report Period - period lookups
	("tabeBalance Report Period", "period_code", "idx_period_code", True),
	("tabeBalance Report Period", "environment", "idx_period_env", False),
]

# Composite indexes for common queries
COMPOSITE_INDEXES = [
	# GL Entry queries by company + date range + account
	("tabGL Entry", ["company", "posting_date", "is_cancelled"], "idx_gl_company_date_cancel"),
	("tabGL Entry", ["account", "posting_date", "is_cancelled"], "idx_gl_account_date_cancel"),
	
	# Account queries by company + root_type
	("tabAccount", ["company", "root_type", "is_group"], "idx_account_company_root"),
	
	# MOF Mapping fast filter
	("tabMOF Account Mapping", ["enabled", "is_group", "mof_account_number"], "idx_mof_filter"),
]


def create_indexes():
	"""Create all eBalance indexes"""
	created = 0
	skipped = 0
	errors = []
	
	# Simple indexes
	for table, column, index_name, unique in INDEXES:
		try:
			if not index_exists(table, index_name):
				create_index(table, column, index_name, unique)
				created += 1
			else:
				skipped += 1
		except Exception as e:
			errors.append(f"{table}.{index_name}: {str(e)}")
	
	# Composite indexes
	for table, columns, index_name in COMPOSITE_INDEXES:
		try:
			if not index_exists(table, index_name):
				create_composite_index(table, columns, index_name)
				created += 1
			else:
				skipped += 1
		except Exception as e:
			errors.append(f"{table}.{index_name}: {str(e)}")
	
	result = {
		"created": created,
		"skipped": skipped,
		"errors": errors
	}
	
	print(f"✅ Created {created} indexes, skipped {skipped} existing")
	if errors:
		print(f"⚠️ Errors: {len(errors)}")
		for e in errors:
			print(f"  - {e}")
	
	return result


def index_exists(table: str, index_name: str) -> bool:
	"""Check if index exists on table"""
	try:
		result = frappe.db.sql("""
			SELECT COUNT(*) as cnt
			FROM information_schema.statistics
			WHERE table_schema = DATABASE()
			AND table_name = %s
			AND index_name = %s
		""", (table, index_name), as_dict=True)
		return bool(result and result[0].get("cnt", 0) > 0)
	except Exception:
		return False


def create_index(table: str, column: str, index_name: str, unique: bool = False):
	"""Create single-column index"""
	unique_str = "UNIQUE " if unique else ""
	sql = f"CREATE {unique_str}INDEX `{index_name}` ON `{table}` (`{column}`)"
	frappe.db.sql_ddl(sql)
	frappe.db.commit()


def create_composite_index(table: str, columns: list, index_name: str):
	"""Create multi-column composite index"""
	cols = ", ".join([f"`{c}`" for c in columns])
	sql = f"CREATE INDEX `{index_name}` ON `{table}` ({cols})"
	frappe.db.sql_ddl(sql)
	frappe.db.commit()


def drop_index(table: str, index_name: str):
	"""Drop index from table"""
	if index_exists(table, index_name):
		sql = f"DROP INDEX `{index_name}` ON `{table}`"
		frappe.db.sql_ddl(sql)
		frappe.db.commit()


def drop_all_indexes():
	"""Drop all eBalance indexes (for cleanup)"""
	dropped = 0
	
	for table, _, index_name, _ in INDEXES:
		try:
			drop_index(table, index_name)
			dropped += 1
		except Exception:
			pass
	
	for table, _, index_name in COMPOSITE_INDEXES:
		try:
			drop_index(table, index_name)
			dropped += 1
		except Exception:
			pass
	
	print(f"✅ Dropped {dropped} indexes")
	return dropped


def analyze_tables():
	"""Analyze tables to update index statistics"""
	tables = [
		"tabMOF Account Mapping",
		"tabMOF Account Mapping Item",
		"tabeBalance Report Request",
		"tabeBalance Submission Log",
		"tabeBalance Report Period",
		"tabGL Entry",
		"tabAccount"
	]
	
	for table in tables:
		try:
			frappe.db.sql(f"ANALYZE TABLE `{table}`")
		except Exception:
			pass
	
	frappe.db.commit()
	print(f"✅ Analyzed {len(tables)} tables")


@frappe.whitelist()
def setup_performance():
	"""One-click performance setup"""
	print("Setting up eBalance performance optimizations...")
	
	# Create indexes
	create_indexes()
	
	# Analyze tables
	analyze_tables()
	
	print("✅ Performance setup complete")
	return {"status": "success"}
