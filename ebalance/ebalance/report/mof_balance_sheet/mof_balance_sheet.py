# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
MOF Balance Sheet (СБТ) Report

Generates Balance Sheet (Санхүү байдлын тайлан) in MOF format
using Mongolian Standard Chart of Accounts (НББОУС) mapping.

This report transforms ERPNext GL Entry data into the standard MOF format
required for eBalance submission.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	"""
	Execute MOF Balance Sheet report.
	
	Args:
		filters: Dict with company, from_date, to_date, fiscal_year
		
	Returns:
		tuple: (columns, data, message, chart, report_summary)
	"""
	filters = frappe._dict(filters or {})
	
	if not filters.company:
		frappe.throw(_("Company is required"))
	
	columns = get_columns()
	data = get_data(filters)
	summary = get_report_summary(data)
	chart = get_chart_data(data)
	
	return columns, data, None, chart, summary


def get_columns():
	"""Return report columns"""
	return [
		{
			"fieldname": "row_code",
			"label": _("Code"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "account_name_mn",
			"label": _("Дансны нэр"),
			"fieldtype": "Data",
			"width": 350
		},
		{
			"fieldname": "account_name",
			"label": _("Account Name"),
			"fieldtype": "Data",
			"width": 250
		},
		{
			"fieldname": "balance",
			"label": _("Balance"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "indent",
			"label": _("Indent"),
			"fieldtype": "Int",
			"width": 0,
			"hidden": 1
		}
	]


def get_data(filters):
	"""Generate Balance Sheet data from MOF Account Mappings"""
	data = []
	
	# Get date range
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	company = filters.company
	
	if filters.fiscal_year and not (from_date and to_date):
		fy = frappe.get_doc("Fiscal Year", filters.fiscal_year)
		from_date = fy.year_start_date
		to_date = fy.year_end_date
	
	# Balance Sheet structure
	bs_structure = [
		# Assets (Хөрөнгө)
		{"row_code": "СБТ.1", "account_name_mn": "НИЙТ ХӨРӨНГӨ", "account_name": "TOTAL ASSETS", "is_total": True, "indent": 0},
		{"row_code": "СБТ.1.1", "account_name_mn": "Эргэлтийн хөрөнгө", "account_name": "Current Assets", "is_total": True, "indent": 1, "mof_range": ["11"]},
		{"row_code": "СБТ.1.1.1", "account_name_mn": "Мөнгө, түүнтэй адилтгах хөрөнгө", "account_name": "Cash and cash equivalents", "indent": 2, "mof_codes": ["1110", "1111", "1112", "1113", "1114"]},
		{"row_code": "СБТ.1.1.2", "account_name_mn": "Богино хугацаат хадгаламж", "account_name": "Short-term deposits", "indent": 2, "mof_codes": ["1120"]},
		{"row_code": "СБТ.1.1.3", "account_name_mn": "Авлага", "account_name": "Trade receivables", "indent": 2, "mof_codes": ["1200", "1201", "1202", "1203", "1204"]},
		{"row_code": "СБТ.1.1.4", "account_name_mn": "Бараа материал", "account_name": "Inventories", "indent": 2, "mof_codes": ["1300", "1301", "1302", "1303", "1304", "1305"]},
		{"row_code": "СБТ.1.1.5", "account_name_mn": "Бусад эргэлтийн хөрөнгө", "account_name": "Other current assets", "indent": 2, "mof_codes": ["1400", "1410", "1420", "1430", "1440", "1450", "1460", "1470", "1500", "1600", "1700"]},
		{"row_code": "СБТ.1.2", "account_name_mn": "Эргэлтийн бус хөрөнгө", "account_name": "Non-current Assets", "is_total": True, "indent": 1, "mof_range": ["18", "19"]},
		{"row_code": "СБТ.1.2.1", "account_name_mn": "Үндсэн хөрөнгө", "account_name": "Property, plant and equipment", "indent": 2, "mof_codes": ["1800", "1801", "1802", "1803", "1804", "1805", "1810"]},
		{"row_code": "СБТ.1.2.2", "account_name_mn": "Хуримтлагдсан элэгдэл", "account_name": "Accumulated depreciation", "indent": 2, "mof_codes": ["1820", "1821", "1822", "1829"]},
		{"row_code": "СБТ.1.2.3", "account_name_mn": "Биет бус хөрөнгө", "account_name": "Intangible assets", "indent": 2, "mof_codes": ["1900", "1901", "1902", "1903", "1910"]},
		{"row_code": "СБТ.1.2.4", "account_name_mn": "Бусад эргэлтийн бус хөрөнгө", "account_name": "Other non-current assets", "indent": 2, "mof_codes": ["1950", "1951", "1952", "1960", "1970", "1980", "1990"]},
		
		# Liabilities (Өр төлбөр)
		{"row_code": "СБТ.2", "account_name_mn": "НИЙТ ӨР ТӨЛБӨР", "account_name": "TOTAL LIABILITIES", "is_total": True, "indent": 0},
		{"row_code": "СБТ.2.1", "account_name_mn": "Богино хугацаат өр төлбөр", "account_name": "Current Liabilities", "is_total": True, "indent": 1, "mof_range": ["21", "22", "23"]},
		{"row_code": "СБТ.2.1.1", "account_name_mn": "Нийлүүлэгчдэд өгөх өр", "account_name": "Trade payables", "indent": 2, "mof_codes": ["2110"]},
		{"row_code": "СБТ.2.1.2", "account_name_mn": "Богино хугацаат зээл", "account_name": "Short-term loans", "indent": 2, "mof_codes": ["2120", "2130", "2140"]},
		{"row_code": "СБТ.2.1.3", "account_name_mn": "Урьдчилгаа", "account_name": "Advances received", "indent": 2, "mof_codes": ["2150"]},
		{"row_code": "СБТ.2.1.4", "account_name_mn": "Бусад өглөг", "account_name": "Other payables", "indent": 2, "mof_codes": ["2160", "2170", "2180", "2190"]},
		{"row_code": "СБТ.2.1.5", "account_name_mn": "Татварын өглөг", "account_name": "Taxes payable", "indent": 2, "mof_codes": ["2200", "2210", "2220", "2230", "2240", "2250", "2300", "2310", "2320", "2330"]},
		{"row_code": "СБТ.2.2", "account_name_mn": "Урт хугацаат өр төлбөр", "account_name": "Non-current Liabilities", "is_total": True, "indent": 1, "mof_range": ["24"]},
		{"row_code": "СБТ.2.2.1", "account_name_mn": "Урт хугацаат зээл", "account_name": "Long-term loans", "indent": 2, "mof_codes": ["2400", "2410", "2420", "2430", "2440"]},
		{"row_code": "СБТ.2.2.2", "account_name_mn": "Бусад урт хугацаат өр", "account_name": "Other non-current liabilities", "indent": 2, "mof_codes": ["2450", "2460", "2490"]},
		
		# Equity (Өмч)
		{"row_code": "СБТ.3", "account_name_mn": "НИЙТ ӨМЧ", "account_name": "TOTAL EQUITY", "is_total": True, "indent": 0},
		{"row_code": "СБТ.3.1", "account_name_mn": "Хувь нийлүүлсэн хөрөнгө", "account_name": "Share capital", "indent": 1, "mof_codes": ["3100", "3110", "3120"]},
		{"row_code": "СБТ.3.2", "account_name_mn": "Давхардуулан төлсөн хөрөнгө", "account_name": "Additional paid-in capital", "indent": 1, "mof_codes": ["3200"]},
		{"row_code": "СБТ.3.3", "account_name_mn": "Хуримтлагдсан ашиг", "account_name": "Retained earnings", "indent": 1, "mof_codes": ["3300", "3310"]},
		{"row_code": "СБТ.3.4", "account_name_mn": "Нөөцийн сан", "account_name": "Reserves", "indent": 1, "mof_codes": ["3400", "3410", "3420"]},
		{"row_code": "СБТ.3.5", "account_name_mn": "Дахин худалдаж авсан хувьцаа", "account_name": "Treasury shares", "indent": 1, "mof_codes": ["3500", "3600"]},
	]
	
	# Calculate balances
	balances = {}
	
	for row in bs_structure:
		if row.get("mof_codes"):
			balance = get_mof_account_balance(
				company, from_date, to_date, row["mof_codes"]
			)
			balances[row["row_code"]] = balance
	
	# Calculate totals
	balances["СБТ.1.1"] = sum(balances.get(f"СБТ.1.1.{i}", 0) for i in range(1, 6))
	balances["СБТ.1.2"] = sum(balances.get(f"СБТ.1.2.{i}", 0) for i in range(1, 5))
	balances["СБТ.1"] = balances.get("СБТ.1.1", 0) + balances.get("СБТ.1.2", 0)
	
	balances["СБТ.2.1"] = sum(balances.get(f"СБТ.2.1.{i}", 0) for i in range(1, 6))
	balances["СБТ.2.2"] = sum(balances.get(f"СБТ.2.2.{i}", 0) for i in range(1, 3))
	balances["СБТ.2"] = balances.get("СБТ.2.1", 0) + balances.get("СБТ.2.2", 0)
	
	balances["СБТ.3"] = sum(balances.get(f"СБТ.3.{i}", 0) for i in range(1, 6))
	
	# Build report data
	for row in bs_structure:
		data.append({
			"row_code": row["row_code"],
			"account_name_mn": row["account_name_mn"],
			"account_name": row["account_name"],
			"balance": flt(balances.get(row["row_code"], 0), 2),
			"indent": row.get("indent", 0),
			"is_total": row.get("is_total", False)
		})
	
	# Add balance check row
	balance_check = balances.get("СБТ.1", 0) - (balances.get("СБТ.2", 0) + balances.get("СБТ.3", 0))
	data.append({
		"row_code": "",
		"account_name_mn": "ТЭНЦЭЛ ШАЛГАХ (A = L + E)",
		"account_name": "Balance Check (A = L + E)",
		"balance": flt(balance_check, 2),
		"indent": 0,
		"is_total": True
	})
	
	return data


def get_mof_account_balance(company, from_date, to_date, mof_codes):
	"""
	Get balance from MOF Account Mappings.
	
	Args:
		company: Company name
		from_date: Start date
		to_date: End date
		mof_codes: List of MOF account codes
		
	Returns:
		float: Total balance
	"""
	total = 0.0
	
	for mof_code in mof_codes:
		if frappe.db.exists("MOF Account Mapping", mof_code):
			doc = frappe.get_doc("MOF Account Mapping", mof_code)
			balance = doc.get_balance(company, from_date, to_date)
			total += balance
	
	return total


def get_report_summary(data):
	"""Generate report summary cards"""
	total_assets = 0
	total_liabilities = 0
	total_equity = 0
	
	for row in data:
		if row.get("row_code") == "СБТ.1":
			total_assets = row.get("balance", 0)
		elif row.get("row_code") == "СБТ.2":
			total_liabilities = row.get("balance", 0)
		elif row.get("row_code") == "СБТ.3":
			total_equity = row.get("balance", 0)
	
	return [
		{
			"value": total_assets,
			"label": _("Total Assets"),
			"datatype": "Currency",
			"currency": frappe.db.get_default("currency")
		},
		{
			"value": total_liabilities,
			"label": _("Total Liabilities"),
			"datatype": "Currency",
			"currency": frappe.db.get_default("currency")
		},
		{
			"value": total_equity,
			"label": _("Total Equity"),
			"datatype": "Currency",
			"currency": frappe.db.get_default("currency")
		}
	]


def get_chart_data(data):
	"""Generate chart data"""
	total_assets = 0
	total_liabilities = 0
	total_equity = 0
	
	for row in data:
		if row.get("row_code") == "СБТ.1":
			total_assets = row.get("balance", 0)
		elif row.get("row_code") == "СБТ.2":
			total_liabilities = row.get("balance", 0)
		elif row.get("row_code") == "СБТ.3":
			total_equity = row.get("balance", 0)
	
	return {
		"data": {
			"labels": [_("Assets"), _("Liabilities"), _("Equity")],
			"datasets": [
				{
					"name": _("Balance Sheet"),
					"values": [total_assets, total_liabilities, total_equity]
				}
			]
		},
		"type": "bar",
		"colors": ["#5e64ff", "#ff5858", "#29cd42"]
	}
