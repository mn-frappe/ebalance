# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
MOF Account Mapping - Maps Mongolian НББОУС standard accounts to ERPNext Chart of Accounts

The Ministry of Finance requires financial reports using the standard 154-account
chart defined in mn_chart.csv. This DocType enables mapping ERPNext accounts
to MOF codes for accurate Balance Sheet (СБТ) and Income Statement (ОҮТ) generation.
"""

import frappe
from frappe.model.document import Document


class MOFAccountMapping(Document):
	"""
	MOF Account Mapping DocType
	
	Maps Mongolian Standard Chart of Accounts (НББОУС) codes to ERPNext accounts.
	Used for eBalance report generation and submission to Ministry of Finance.
	
	Account Structure:
		1xxx - Assets (Хөрөнгө)
		2xxx - Liabilities (Өр төлбөр)
		3xxx - Equity (Өмч)
		4xxx - Revenue/Income (Орлого)
		5xxx - Cost of Sales (Борлуулалтын өртөг)
		6xxx - Operating Expenses (Үйл ажиллагааны зардал)
		7xxx - Finance Costs (Санхүүгийн зардал)
		8xxx - Other Expenses (Бусад зардал)
		9xxx - Tax & Off-balance (Татвар, тэнцлийн гаднах)
	"""
	
	def validate(self):
		"""Validate MOF account mapping"""
		self.validate_account_number()
		self.validate_parent()
		self.validate_mapped_accounts()
	
	def validate_account_number(self):
		"""Validate MOF account number format"""
		if not self.mof_account_number:
			return
			
		# Must be numeric 4-digit code
		if not self.mof_account_number.isdigit():
			frappe.throw(
				frappe._("MOF Account Number must be numeric (e.g., 1111, 2110)"),
				title=frappe._("Invalid Account Number")
			)
		
		# Validate root type matches account range
		account_range = int(self.mof_account_number[0])
		expected_root_types = {
			1: "Asset",
			2: "Liability",
			3: "Equity",
			4: "Income",
			5: "Expense",
			6: "Expense",
			7: "Expense",
			8: "Expense",
			9: "Expense"  # Includes off-balance (Asset category)
		}
		
		if account_range in expected_root_types:
			expected = expected_root_types[account_range]
			# 9900 series is off-balance (Asset type)
			if self.mof_account_number.startswith("99"):
				expected = "Asset"
			
			if self.root_type and self.root_type != expected:
				frappe.msgprint(
					frappe._("Account {0} typically has root type {1}, but {2} was selected").format(
						self.mof_account_number, expected, self.root_type
					),
					indicator="orange",
					title=frappe._("Root Type Notice")
				)
	
	def validate_parent(self):
		"""Validate parent account relationship"""
		if self.parent_mof_account:
			parent = frappe.get_doc("MOF Account Mapping", self.parent_mof_account)
			if not parent.is_group:
				frappe.throw(
					frappe._("Parent account {0} must be a group account").format(
						self.parent_mof_account
					),
					title=frappe._("Invalid Parent")
				)
	
	def validate_mapped_accounts(self):
		"""Validate mapped ERPNext accounts"""
		if not self.mapped_accounts:
			return
			
		# Check for duplicate mappings
		accounts = [row.account for row in self.mapped_accounts if row.account]
		if len(accounts) != len(set(accounts)):
			frappe.throw(
				frappe._("Duplicate ERPNext accounts in mapping"),
				title=frappe._("Duplicate Mapping")
			)
		
		# Validate account root types match
		for row in self.mapped_accounts:
			if row.account:
				erp_root_type = frappe.db.get_value("Account", row.account, "root_type")
				if erp_root_type and erp_root_type != self.root_type:
					frappe.msgprint(
						frappe._("ERPNext account {0} has root type {1}, MOF account has {2}").format(
							row.account, erp_root_type, self.root_type
						),
						indicator="orange",
						title=frappe._("Root Type Mismatch")
					)
	
	def get_balance(self, company, from_date=None, to_date=None):
		"""
		Get total balance from all mapped ERPNext accounts.
		
		Args:
			company: Company name
			from_date: Start date (optional, defaults to fiscal year start)
			to_date: End date (optional, defaults to today)
			
		Returns:
			float: Total balance (debit - credit for Asset/Expense, credit - debit for others)
		"""
		if not self.mapped_accounts:
			return 0.0
		
		total = 0.0
		for row in self.mapped_accounts:
			if row.account and row.enabled:
				balance = get_account_balance(
					row.account, company, from_date, to_date
				)
				total += balance * (row.weight or 1.0)
		
		return total


def get_account_balance(account, company, from_date=None, to_date=None):
	"""
	Get account balance from GL Entry.
	
	Args:
		account: ERPNext Account name
		company: Company name
		from_date: Optional start date
		to_date: Optional end date
		
	Returns:
		float: Account balance
	"""
	filters = {
		"account": account,
		"company": company,
		"is_cancelled": 0
	}
	
	if from_date:
		filters["posting_date"] = (">=", from_date)
	if to_date:
		filters["posting_date"] = ("<=", to_date)
	
	# Get sum of debits and credits
	result = frappe.db.sql("""
		SELECT 
			SUM(debit) as total_debit,
			SUM(credit) as total_credit
		FROM `tabGL Entry`
		WHERE account = %s
		AND company = %s
		AND is_cancelled = 0
		{date_filter}
	""".format(
		date_filter="AND posting_date BETWEEN %s AND %s" if from_date and to_date else ""
	), (account, company, from_date, to_date) if from_date and to_date else (account, company), as_dict=True)
	
	if result:
		total_debit = result[0].get("total_debit") or 0
		total_credit = result[0].get("total_credit") or 0
		
		# Get root type
		root_type = frappe.db.get_value("Account", account, "root_type")
		
		# Asset and Expense accounts: debit - credit
		# Liability, Equity, Income accounts: credit - debit
		if root_type in ("Asset", "Expense"):
			return total_debit - total_credit
		else:
			return total_credit - total_debit
	
	return 0.0


@frappe.whitelist()
def get_unmapped_accounts(company):
	"""
	Get ERPNext accounts not yet mapped to MOF codes.
	
	Args:
		company: Company name
		
	Returns:
		list: Unmapped accounts with name, account_name, root_type
	"""
	# Get all mapped accounts
	mapped = frappe.db.sql("""
		SELECT DISTINCT mai.account
		FROM `tabMOF Account Mapping Item` mai
		INNER JOIN `tabMOF Account Mapping` mam ON mai.parent = mam.name
		WHERE mai.account IS NOT NULL
	""", as_list=True)
	
	mapped_accounts = [row[0] for row in mapped]
	
	# Get unmapped accounts (leaf accounts only)
	filters = {
		"company": company,
		"is_group": 0,
		"disabled": 0
	}
	
	if mapped_accounts:
		filters["name"] = ("not in", mapped_accounts)
	
	return frappe.get_all(
		"Account",
		filters=filters,
		fields=["name", "account_name", "root_type", "parent_account"],
		order_by="account_number, name"
	)


@frappe.whitelist()
def auto_map_accounts(company):
	"""
	Auto-map ERPNext accounts to MOF codes based on account names/patterns.
	
	Args:
		company: Company name
		
	Returns:
		dict: Mapping results with success count and errors
	"""
	# Mapping patterns: MOF code -> ERPNext account name patterns
	patterns = {
		"1111": ["cash", "кассан", "бэлэн мөнгө"],
		"1112": ["bank", "харилцах", "checking", "current account"],
		"1113": ["foreign currency", "валют"],
		"1201": ["receivable", "авлага", "debtors"],
		"1301": ["raw material", "түүхий эд"],
		"1304": ["merchandise", "бараа", "stock", "inventory"],
		"1801": ["land", "газар"],
		"1802": ["building", "барилга"],
		"1803": ["machinery", "machine", "equipment", "тоног төхөөрөмж"],
		"1804": ["vehicle", "тээврийн", "car", "truck"],
		"2110": ["payable", "creditor", "өглөг", "supplier"],
		"2120": ["bank loan", "зээл"],
		"2160": ["salary", "wage", "цалин"],
		"2210": ["vat", "нөат", "value added"],
		"3110": ["share capital", "capital", "хувь нийлүүлсэн"],
		"3310": ["retained", "profit", "loss", "ашиг", "алдагдал"],
		"4110": ["sales", "revenue", "орлого", "борлуулалт"],
		"4120": ["service", "үйлчилгээ"],
		"5110": ["cost of goods", "cost of sales", "өртөг"],
		"6210": ["salary expense", "wage expense", "цалингийн зардал"],
		"6230": ["rent", "түрээс"],
		"6310": ["depreciation", "элэгдэл"],
	}
	
	success_count = 0
	errors = []
	
	# Get all ERPNext accounts
	accounts = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "disabled": 0},
		fields=["name", "account_name", "root_type"]
	)
	
	for account in accounts:
		account_name_lower = (account.account_name or "").lower()
		
		for mof_code, keywords in patterns.items():
			if any(keyword.lower() in account_name_lower for keyword in keywords):
				# Check if MOF mapping exists
				if frappe.db.exists("MOF Account Mapping", mof_code):
					try:
						# Add to existing mapping
						doc = frappe.get_doc("MOF Account Mapping", mof_code)
						
						# Check if already mapped
						existing = [r.account for r in doc.mapped_accounts]
						if account.name not in existing:
							doc.append("mapped_accounts", {
								"account": account.name,
								"enabled": 1,
								"weight": 1.0
							})
							doc.auto_mapped = 1
							doc.save(ignore_permissions=True)
							success_count += 1
					except Exception as e:
						errors.append(f"{account.name}: {str(e)}")
				break
	
	frappe.db.commit()
	
	return {
		"success_count": success_count,
		"errors": errors,
		"message": f"Auto-mapped {success_count} accounts"
	}


@frappe.whitelist()
def get_mof_balance_report(company, from_date, to_date):
	"""
	Generate MOF balance report data.
	
	Args:
		company: Company name
		from_date: Report start date
		to_date: Report end date
		
	Returns:
		list: MOF account balances for report generation
	"""
	report_data = []
	
	# Get all enabled MOF mappings with accounts
	mappings = frappe.get_all(
		"MOF Account Mapping",
		filters={"enabled": 1, "is_group": 0},
		fields=["name", "mof_account_number", "mof_account_name", 
				"mof_account_name_mn", "root_type"],
		order_by="mof_account_number"
	)
	
	for mapping in mappings:
		doc = frappe.get_doc("MOF Account Mapping", mapping.name)
		balance = doc.get_balance(company, from_date, to_date)
		
		if balance != 0:  # Only include accounts with balances
			report_data.append({
				"mof_code": mapping.mof_account_number,
				"account_name": mapping.mof_account_name,
				"account_name_mn": mapping.mof_account_name_mn,
				"root_type": mapping.root_type,
				"balance": balance
			})
	
	return report_data
