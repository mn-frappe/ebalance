# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportArgumentType=false

"""
eBalance Report Transformer

Transforms ERPNext Trial Balance data to MOF eBalance format for submission.

The Ministry of Finance requires financial reports in a specific cell-based format:
- Each form (СБТ, ОҮТ, etc.) has rows and columns
- Each cell has a unique ID from the eBalance API
- Cell values are submitted as cellModelList: [{id: 12345, cellValue: "1000.00"}, ...]

This module:
1. Fetches cell IDs from eBalance API (getReportData)
2. Calculates values from ERPNext GL Entries using MOF Account Mappings
3. Formats data for submission via saveReportData/sendReportData APIs
"""

import frappe
from frappe.utils import flt


class ReportTransformer:
    """
    Transforms ERPNext data to MOF eBalance format.

    Usage:
        transformer = ReportTransformer(company, fiscal_year)

        # Generate Balance Sheet data
        cell_data = transformer.generate_balance_sheet()

        # Generate Income Statement data
        cell_data = transformer.generate_income_statement()

        # Get all report data for submission
        submission_data = transformer.get_submission_data(report_user_org_hdr_id)
    """

    # Form codes and their Mongolian names
    FORM_CODES = {
        "SBT-Jiliin": "Санхүү байдлын тайлан - Жилийн эцэс",
        "SBT-Hagas": "Санхүү байдлын тайлан - Хагас жил",
        "OUT-Jiliin": "Орлогын үр дүнгийн тайлан - Жилийн эцэс",
        "OUT-Hagas": "Орлогын үр дүнгийн тайлан - Хагас жил",
        "MGT-Jiliin": "Мөнгөн гүйлгээний тайлан - Жилийн эцэс",
        "MGT-Hagas": "Мөнгөн гүйлгээний тайлан - Хагас жил",
        "OMT-Jiliin": "Өмчийн өөрчлөлтийн тайлан - Жилийн эцэс",
        "OMT-Hagas": "Өмчийн өөрчлөлтийн тайлан - Хагас жил"
    }

    # Balance Sheet row structure mapping to MOF accounts
    # СБТ row code -> list of MOF account number prefixes
    BALANCE_SHEET_MAPPING = {
        # Assets (Хөрөнгө)
        "СБТ.1": None,  # Total Assets - calculated
        "СБТ.1.1": None,  # Current Assets - calculated
        "СБТ.1.1.1": ["1110", "1111", "1112", "1113", "1114"],  # Cash and equivalents
        "СБТ.1.1.2": ["1120"],  # Short-term deposits
        "СБТ.1.1.3": ["1200", "1201", "1202", "1203", "1204"],  # Trade receivables (excl allowance)
        "СБТ.1.1.4": ["1300", "1301", "1302", "1303", "1304", "1305"],  # Inventories (excl allowance)
        "СБТ.1.1.5": ["1400", "1410", "1420", "1430", "1440", "1450", "1460", "1470"],  # Other current
        "СБТ.1.2": None,  # Non-current Assets - calculated
        "СБТ.1.2.1": ["1800", "1801", "1802", "1803", "1804", "1805", "1810"],  # PPE
        "СБТ.1.2.2": ["1820", "1821", "1822", "1829"],  # Accumulated depreciation
        "СБТ.1.2.3": ["1900", "1901", "1902", "1903"],  # Intangible assets
        "СБТ.1.2.4": ["1950", "1951", "1952", "1960", "1970", "1980", "1990"],  # Other non-current

        # Liabilities (Өр төлбөр)
        "СБТ.2": None,  # Total Liabilities - calculated
        "СБТ.2.1": None,  # Current Liabilities - calculated
        "СБТ.2.1.1": ["2110"],  # Trade payables
        "СБТ.2.1.2": ["2120", "2130", "2140"],  # Short-term loans
        "СБТ.2.1.3": ["2150"],  # Advances received
        "СБТ.2.1.4": ["2160", "2170", "2180", "2190"],  # Other payables
        "СБТ.2.1.5": ["2200", "2210", "2220", "2230", "2240", "2250"],  # Taxes payable
        "СБТ.2.2": None,  # Non-current Liabilities - calculated
        "СБТ.2.2.1": ["2400", "2410", "2420", "2430", "2440"],  # Long-term loans
        "СБТ.2.2.2": ["2450", "2460", "2490"],  # Other non-current

        # Equity (Өмч)
        "СБТ.3": None,  # Total Equity - calculated
        "СБТ.3.1": ["3100", "3110", "3120"],  # Share capital
        "СБТ.3.2": ["3200"],  # Additional paid-in capital
        "СБТ.3.3": ["3300", "3310"],  # Retained earnings
        "СБТ.3.4": ["3400", "3410", "3420"],  # Reserves
        "СБТ.3.5": ["3500"],  # Treasury shares
    }

    # Income Statement row structure
    INCOME_STATEMENT_MAPPING = {
        "ОҮТ.1": ["4000", "4100", "4110", "4120", "4130", "4140"],  # Revenue
        "ОҮТ.2": ["5000", "5100", "5110", "5120", "5130"],  # Cost of sales
        "ОҮТ.3": None,  # Gross profit - calculated (ОҮТ.1 - ОҮТ.2)
        "ОҮТ.4": ["4200", "4210", "4220", "4230"],  # Other operating income
        "ОҮТ.5": ["6000", "6100", "6110", "6120", "6130"],  # Selling expenses
        "ОҮТ.6": ["6200", "6210", "6220", "6230", "6240", "6250", "6260"],  # Admin expenses
        "ОҮТ.7": ["6300", "6310", "6320"],  # Depreciation
        "ОҮТ.8": ["6400", "6410", "6420", "6500", "6600", "6700", "6800"],  # Other operating expenses
        "ОҮТ.9": None,  # Operating profit - calculated
        "ОҮТ.10": ["4300", "4310", "4320", "4330", "4400"],  # Finance income
        "ОҮТ.11": ["7000", "7100", "7200", "7300"],  # Finance costs
        "ОҮТ.12": ["8000", "8100", "8200", "8300"],  # Other expenses
        "ОҮТ.13": None,  # Profit before tax - calculated
        "ОҮТ.14": ["9000", "9100", "9200", "9300"],  # Income tax expense
        "ОҮТ.15": None,  # Net profit - calculated
    }

    def __init__(self, company, fiscal_year=None, from_date=None, to_date=None):
        """
        Initialize transformer.

        Args:
            company: Company name
            fiscal_year: Fiscal Year document name (optional)
            from_date: Report start date (optional)
            to_date: Report end date (optional)
        """
        self.company = company
        self.fiscal_year = fiscal_year
        self.from_date = from_date
        self.to_date = to_date

        # Set dates from fiscal year if not provided
        if fiscal_year and not (from_date and to_date):
            fy = frappe.get_doc("Fiscal Year", fiscal_year)
            self.from_date = fy.year_start_date
            self.to_date = fy.year_end_date

        # Cache for cell IDs from eBalance API
        self._cell_ids = {}
        self._form_data = {}

    def load_cell_ids(self, report_data):
        """
        Load cell IDs from eBalance getReportData response.

        Args:
            report_data: Response from getReportData API
        """
        if not report_data:
            return

        reports = report_data.get("reports", [])
        for report in reports:
            form_data_list = report.get("reportFormData", [])
            for form_data in form_data_list:
                form_code = form_data.get("formCode")
                form_id = form_data.get("formId")

                self._form_data[form_code] = {
                    "form_id": form_id,
                    "form_name": form_data.get("formName"),
                    "rows": {}
                }

                # Map row names to cell IDs
                for row in form_data.get("reportFormRowList", []):
                    row_name = row.get("name")  # e.g., "СБТ.1.1.1"
                    row_id = row.get("id")

                    self._form_data[form_code]["rows"][row_name] = {
                        "id": row_id,
                        "order": row.get("rowOrder")
                    }
                    self._cell_ids[f"{form_code}:{row_name}"] = row_id

    def _preload_balances(self):
        """
        Preload all GL balances in a single query for performance.

        Instead of querying per MOF account, fetch all balances at once
        and cache them for the report generation session.
        """
        if hasattr(self, "_balance_cache") and self._balance_cache:
            return

        self._balance_cache = {}

        # Get all mapped accounts with their MOF codes
        mapping_items = frappe.db.sql("""
            SELECT
                mi.account,
                m.mof_account_number,
                m.root_type
            FROM `tabMOF Account Mapping Item` mi
            JOIN `tabMOF Account Mapping` m ON m.name = mi.parent
            WHERE m.enabled = 1 AND m.is_group = 0
        """, as_dict=True)

        if not mapping_items:
            return

        # Build account -> MOF code lookup
        account_to_mof = {item.account: item.mof_account_number for item in mapping_items}
        mof_root_types = {item.mof_account_number: item.root_type for item in mapping_items}
        accounts = list(account_to_mof.keys())

        if not accounts:
            return

        # Single query for all GL balances
        gl_data = frappe.db.sql("""
            SELECT
                account,
                SUM(debit) as total_debit,
                SUM(credit) as total_credit
            FROM `tabGL Entry`
            WHERE account IN %(accounts)s
            AND company = %(company)s
            AND is_cancelled = 0
            AND posting_date BETWEEN %(from_date)s AND %(to_date)s
            GROUP BY account
        """, {
            "accounts": accounts,
            "company": self.company,
            "from_date": self.from_date,
            "to_date": self.to_date
        }, as_dict=True)

        # Calculate balance for each MOF code
        mof_balances = {}

        for row in gl_data:
            mof_code = account_to_mof.get(row.account)
            if not mof_code:
                continue

            debit = flt(row.total_debit)
            credit = flt(row.total_credit)
            root_type = mof_root_types.get(mof_code)

            # Determine balance based on root type
            if root_type in ("Asset", "Expense"):
                balance = debit - credit
            else:
                balance = credit - debit

            if mof_code not in mof_balances:
                mof_balances[mof_code] = 0.0
            mof_balances[mof_code] += balance

        self._balance_cache = mof_balances

    def get_account_balance(self, mof_account_prefixes):
        """
        Get total balance for MOF accounts matching prefixes (Optimized).

        Uses preloaded balance cache for O(1) lookups.

        Args:
            mof_account_prefixes: List of MOF account number prefixes

        Returns:
            float: Total balance
        """
        if not mof_account_prefixes:
            return 0.0

        # Ensure balances are preloaded
        self._preload_balances()

        total = 0.0

        # Match prefixes against cached balances
        for prefix in mof_account_prefixes:
            for mof_code, balance in self._balance_cache.items():
                if mof_code.startswith(prefix):
                    total += balance

        return total

    def get_account_balance_legacy(self, mof_account_prefixes):
        """
        Get total balance for MOF accounts matching prefixes (Legacy - slower).

        Args:
            mof_account_prefixes: List of MOF account number prefixes

        Returns:
            float: Total balance
        """
        if not mof_account_prefixes:
            return 0.0

        total = 0.0

        for prefix in mof_account_prefixes:
            # Get all MOF Account Mappings matching prefix
            mappings = frappe.get_all(
                "MOF Account Mapping",
                filters={
                    "enabled": 1,
                    "is_group": 0,
                    "mof_account_number": ("like", f"{prefix}%")
                },
                fields=["name"]
            )

            for mapping in mappings:
                doc = frappe.get_doc("MOF Account Mapping", mapping.name)
                balance = doc.get_balance(self.company, self.from_date, self.to_date)
                total += balance

        return total

    def get_gl_balance_by_root_type(self, root_types, account_range=None):
        """
        Get balance directly from GL Entry for accounts of given root types.

        Args:
            root_types: List of root types (Asset, Liability, etc.)
            account_range: Optional tuple (start, end) for account numbers

        Returns:
            float: Total balance
        """
        filters = {
            "company": self.company,
            "is_cancelled": 0
        }

        if self.from_date and self.to_date:
            filters["posting_date"] = ("between", [self.from_date, self.to_date])

        # Get accounts of specified root types
        account_filters = {
            "company": self.company,
            "root_type": ("in", root_types),
            "is_group": 0,
            "disabled": 0
        }

        accounts = frappe.get_all("Account", filters=account_filters, pluck="name")

        if not accounts:
            return 0.0

        # Sum GL entries - use parameterized query
        result = frappe.db.sql("""
            SELECT
                SUM(debit) as total_debit,
                SUM(credit) as total_credit
            FROM `tabGL Entry`
            WHERE account IN %(accounts)s
            AND company = %(company)s
            AND is_cancelled = 0
            AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        """, {
            "accounts": accounts,
            "company": self.company,
            "from_date": self.from_date,
            "to_date": self.to_date
        }, as_dict=True)

        if result:
            total_debit = flt(result[0].get("total_debit"))
            total_credit = flt(result[0].get("total_credit"))

            # Asset and Expense: debit balance, others: credit balance
            if root_types[0] in ("Asset", "Expense"):
                return total_debit - total_credit
            else:
                return total_credit - total_debit

        return 0.0

    def generate_balance_sheet(self, form_code="SBT-Jiliin"):
        """
        Generate Balance Sheet (СБТ) data.

        Args:
            form_code: Form code (SBT-Jiliin or SBT-Hagas)

        Returns:
            list: Cell data for submission [{id, cellValue}, ...]
        """
        cell_data = []
        row_values = {}

        # Calculate leaf rows first
        for row_code, account_prefixes in self.BALANCE_SHEET_MAPPING.items():
            if account_prefixes:  # Leaf node
                value = self.get_account_balance(account_prefixes)
                row_values[row_code] = value

        # Calculate totals
        # СБТ.1.1 = sum of СБТ.1.1.x
        row_values["СБТ.1.1"] = sum(
            row_values.get(f"СБТ.1.1.{i}", 0) for i in range(1, 6)
        )

        # СБТ.1.2 = sum of СБТ.1.2.x
        row_values["СБТ.1.2"] = sum(
            row_values.get(f"СБТ.1.2.{i}", 0) for i in range(1, 5)
        )

        # СБТ.1 = СБТ.1.1 + СБТ.1.2 (Total Assets)
        row_values["СБТ.1"] = row_values.get("СБТ.1.1", 0) + row_values.get("СБТ.1.2", 0)

        # СБТ.2.1 = sum of СБТ.2.1.x
        row_values["СБТ.2.1"] = sum(
            row_values.get(f"СБТ.2.1.{i}", 0) for i in range(1, 6)
        )

        # СБТ.2.2 = sum of СБТ.2.2.x
        row_values["СБТ.2.2"] = sum(
            row_values.get(f"СБТ.2.2.{i}", 0) for i in range(1, 3)
        )

        # СБТ.2 = СБТ.2.1 + СБТ.2.2 (Total Liabilities)
        row_values["СБТ.2"] = row_values.get("СБТ.2.1", 0) + row_values.get("СБТ.2.2", 0)

        # СБТ.3 = sum of СБТ.3.x (Total Equity)
        row_values["СБТ.3"] = sum(
            row_values.get(f"СБТ.3.{i}", 0) for i in range(1, 6)
        )

        # Build cell data for submission
        for row_code, value in row_values.items():
            cell_key = f"{form_code}:{row_code}"
            cell_id = self._cell_ids.get(cell_key)

            if cell_id:
                cell_data.append({
                    "id": cell_id,
                    "cellValue": str(flt(value, 2))
                })

        return cell_data

    def generate_income_statement(self, form_code="OUT-Jiliin"):
        """
        Generate Income Statement (ОҮТ) data.

        Args:
            form_code: Form code (OUT-Jiliin or OUT-Hagas)

        Returns:
            list: Cell data for submission
        """
        cell_data = []
        row_values = {}

        # Calculate leaf rows
        for row_code, account_prefixes in self.INCOME_STATEMENT_MAPPING.items():
            if account_prefixes:
                value = self.get_account_balance(account_prefixes)
                row_values[row_code] = value

        # Calculate derived rows
        # ОҮТ.3 = ОҮТ.1 - ОҮТ.2 (Gross profit)
        row_values["ОҮТ.3"] = row_values.get("ОҮТ.1", 0) - row_values.get("ОҮТ.2", 0)

        # ОҮТ.9 = ОҮТ.3 + ОҮТ.4 - ОҮТ.5 - ОҮТ.6 - ОҮТ.7 - ОҮТ.8 (Operating profit)
        row_values["ОҮТ.9"] = (
            row_values.get("ОҮТ.3", 0) +
            row_values.get("ОҮТ.4", 0) -
            row_values.get("ОҮТ.5", 0) -
            row_values.get("ОҮТ.6", 0) -
            row_values.get("ОҮТ.7", 0) -
            row_values.get("ОҮТ.8", 0)
        )

        # ОҮТ.13 = ОҮТ.9 + ОҮТ.10 - ОҮТ.11 - ОҮТ.12 (Profit before tax)
        row_values["ОҮТ.13"] = (
            row_values.get("ОҮТ.9", 0) +
            row_values.get("ОҮТ.10", 0) -
            row_values.get("ОҮТ.11", 0) -
            row_values.get("ОҮТ.12", 0)
        )

        # ОҮТ.15 = ОҮТ.13 - ОҮТ.14 (Net profit)
        row_values["ОҮТ.15"] = row_values.get("ОҮТ.13", 0) - row_values.get("ОҮТ.14", 0)

        # Build cell data
        for row_code, value in row_values.items():
            cell_key = f"{form_code}:{row_code}"
            cell_id = self._cell_ids.get(cell_key)

            if cell_id:
                cell_data.append({
                    "id": cell_id,
                    "cellValue": str(flt(value, 2))
                })

        return cell_data

    def get_submission_data(self, report_user_org_hdr_id, forms=None):
        """
        Get complete submission data for all forms.

        Args:
            report_user_org_hdr_id: Report request ID from eBalance
            forms: List of form codes to include (default: all)

        Returns:
            dict: Submission payload for saveReportData API
        """
        forms = forms or ["SBT-Jiliin", "OUT-Jiliin"]

        all_cell_data = []

        for form_code in forms:
            if form_code.startswith("SBT"):
                all_cell_data.extend(self.generate_balance_sheet(form_code))
            elif form_code.startswith("OUT"):
                all_cell_data.extend(self.generate_income_statement(form_code))

        return {
            "reportUserOrgHdrId": report_user_org_hdr_id,
            "cellModelList": all_cell_data
        }


# Frappe whitelisted methods

@frappe.whitelist()
def generate_report_data(company, fiscal_year=None, from_date=None, to_date=None,
                         form_codes=None):
    """
    Generate MOF report data from ERPNext.

    Args:
        company: Company name
        fiscal_year: Fiscal Year name
        from_date: Start date
        to_date: End date
        form_codes: JSON list of form codes

    Returns:
        dict: Generated report data by form
    """
    import json

    if form_codes and isinstance(form_codes, str):
        form_codes = json.loads(form_codes)

    transformer = ReportTransformer(
        company=company,
        fiscal_year=fiscal_year,
        from_date=from_date,
        to_date=to_date
    )

    result = {}

    forms = form_codes or ["SBT-Jiliin", "OUT-Jiliin"]

    for form_code in forms:
        if form_code.startswith("SBT"):
            result[form_code] = transformer.generate_balance_sheet(form_code)
        elif form_code.startswith("OUT"):
            result[form_code] = transformer.generate_income_statement(form_code)

    return result


@frappe.whitelist()
def preview_balance_sheet(company, fiscal_year=None, from_date=None, to_date=None):
    """
    Preview Balance Sheet data before submission.

    Returns human-readable format with row names and values.
    """
    transformer = ReportTransformer(
        company=company,
        fiscal_year=fiscal_year,
        from_date=from_date,
        to_date=to_date
    )

    # Generate values
    row_values = {}

    for row_code, account_prefixes in transformer.BALANCE_SHEET_MAPPING.items():
        if account_prefixes:
            value = transformer.get_account_balance(account_prefixes)
            row_values[row_code] = value

    # Calculate totals
    row_values["СБТ.1.1"] = sum(row_values.get(f"СБТ.1.1.{i}", 0) for i in range(1, 6))
    row_values["СБТ.1.2"] = sum(row_values.get(f"СБТ.1.2.{i}", 0) for i in range(1, 5))
    row_values["СБТ.1"] = row_values.get("СБТ.1.1", 0) + row_values.get("СБТ.1.2", 0)
    row_values["СБТ.2.1"] = sum(row_values.get(f"СБТ.2.1.{i}", 0) for i in range(1, 6))
    row_values["СБТ.2.2"] = sum(row_values.get(f"СБТ.2.2.{i}", 0) for i in range(1, 3))
    row_values["СБТ.2"] = row_values.get("СБТ.2.1", 0) + row_values.get("СБТ.2.2", 0)
    row_values["СБТ.3"] = sum(row_values.get(f"СБТ.3.{i}", 0) for i in range(1, 6))

    # Build preview with labels
    ROW_LABELS = {
        "СБТ.1": "НИЙТ ХӨРӨНГӨ (Total Assets)",
        "СБТ.1.1": "Эргэлтийн хөрөнгө (Current Assets)",
        "СБТ.1.1.1": "Мөнгө, түүнтэй адилтгах хөрөнгө",
        "СБТ.1.1.2": "Богино хугацаат хадгаламж",
        "СБТ.1.1.3": "Авлага",
        "СБТ.1.1.4": "Бараа материал",
        "СБТ.1.1.5": "Бусад эргэлтийн хөрөнгө",
        "СБТ.1.2": "Эргэлтийн бус хөрөнгө (Non-current Assets)",
        "СБТ.1.2.1": "Үндсэн хөрөнгө",
        "СБТ.1.2.2": "Хуримтлагдсан элэгдэл",
        "СБТ.1.2.3": "Биет бус хөрөнгө",
        "СБТ.1.2.4": "Бусад эргэлтийн бус хөрөнгө",
        "СБТ.2": "НИЙТ ӨР ТӨЛБӨР (Total Liabilities)",
        "СБТ.2.1": "Богино хугацаат өр төлбөр (Current Liabilities)",
        "СБТ.2.1.1": "Нийлүүлэгчдэд өгөх өр",
        "СБТ.2.1.2": "Богино хугацаат зээл",
        "СБТ.2.1.3": "Урьдчилгаа",
        "СБТ.2.1.4": "Бусад өглөг",
        "СБТ.2.1.5": "Татварын өглөг",
        "СБТ.2.2": "Урт хугацаат өр төлбөр (Non-current Liabilities)",
        "СБТ.2.2.1": "Урт хугацаат зээл",
        "СБТ.2.2.2": "Бусад урт хугацаат өр",
        "СБТ.3": "НИЙТ ӨМЧ (Total Equity)",
        "СБТ.3.1": "Хувь нийлүүлсэн хөрөнгө",
        "СБТ.3.2": "Давхардуулан төлсөн хөрөнгө",
        "СБТ.3.3": "Хуримтлагдсан ашиг",
        "СБТ.3.4": "Нөөцийн сан",
        "СБТ.3.5": "Дахин худалдаж авсан хувьцаа",
    }

    preview = []
    for row_code in sorted(row_values.keys()):
        preview.append({
            "row_code": row_code,
            "label": ROW_LABELS.get(row_code, row_code),
            "value": flt(row_values[row_code], 2)
        })

    # Validation: Assets = Liabilities + Equity
    total_assets = row_values.get("СБТ.1", 0)
    total_liabilities = row_values.get("СБТ.2", 0)
    total_equity = row_values.get("СБТ.3", 0)

    balance_check = total_assets - (total_liabilities + total_equity)

    return {
        "data": preview,
        "summary": {
            "total_assets": flt(total_assets, 2),
            "total_liabilities": flt(total_liabilities, 2),
            "total_equity": flt(total_equity, 2),
            "balance_check": flt(balance_check, 2),
            "is_balanced": abs(balance_check) < 0.01
        }
    }
