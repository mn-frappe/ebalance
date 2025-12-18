# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportIncompatibleMethodOverride=false

"""
MOF Report Form Row - Maps MOF form rows (СБТ.1, СБТ.1.1) to account aggregations

Ministry of Finance requires financial reports in specific formats:
- СБТ (SBT) - Санхүү байдлын тайлан (Balance Sheet)
- ОҮТ (OUT) - Орлогын үр дүнгийн тайлан (Income Statement)
- МГТ (MGT) - Мөнгөн гүйлгээний тайлан (Cash Flow Statement)
- ӨМТ (OMT) - Өмчийн өөрчлөлтийн тайлан (Statement of Changes in Equity)
"""

import re

import frappe
from frappe.model.document import Document


class MOFReportFormRow(Document):
    """
    MOF Report Form Row DocType

    Maps MOF report form rows to account aggregations.
    Each row in a MOF report (e.g., СБТ.1.1 = Current Assets) is mapped
    to specific MOF account codes to calculate the row value.

    Row Code Examples:
        СБТ.1 - Хөрөнгө (Assets)
        СБТ.1.1 - Эргэлтийн хөрөнгө (Current Assets)
        СБТ.1.1.1 - Мөнгө, түүнтэй адилтгах хөрөнгө (Cash and cash equivalents)
    """

    def validate(self):
        """Validate form row"""
        self.validate_row_code()
        self.validate_formula()

    def validate_row_code(self):
        """Validate row code format"""
        if not self.row_code:
            return

        # Must match pattern: СБТ.X or СБТ.X.X or СБТ.X.X.X
        pattern = r'^(СБТ|ОҮТ|МГТ|ӨМТ)\.\d+(\.\d+)*$'
        if not re.match(pattern, self.row_code):
            # Also allow English codes
            pattern_en = r'^(SBT|OUT|MGT|OMT)\.\d+(\.\d+)*$'
            if not re.match(pattern_en, self.row_code, re.IGNORECASE):
                frappe.throw(
                    frappe._("Row code must be in format СБТ.X.X.X (e.g., СБТ.1.1.1)"),
                    title=frappe._("Invalid Row Code")
                )

    def validate_formula(self):
        """Validate calculation formula syntax"""
        if not self.calculation_formula or not self.is_calculated:
            return

        # Basic validation - check for valid row references
        # Formula example: "СБТ.1.1 + СБТ.1.2 + СБТ.1.3"
        formula = self.calculation_formula

        # Remove operators and whitespace
        tokens = re.split(r'[\+\-\*\/\(\)\s]+', formula)
        tokens = [t.strip() for t in tokens if t.strip()]

        # Each token should be a valid row code or number
        for token in tokens:
            if token and not token.replace('.', '').isdigit():
                # Should be a row code reference
                pattern = r'^(СБТ|ОҮТ|МГТ|ӨМТ|SBT|OUT|MGT|OMT)\.\d+(\.\d+)*$'
                if not re.match(pattern, token, re.IGNORECASE):
                    frappe.throw(
                        frappe._("Invalid formula reference: {0}").format(token),
                        title=frappe._("Formula Error")
                    )

    def calculate_row_value(self, company, from_date, to_date):
        """
        Calculate row value from mapped accounts or formula.

        Args:
            company: Company name
            from_date: Report start date
            to_date: Report end date

        Returns:
            float: Row value
        """
        if self.is_calculated and self.calculation_formula:
            return self.calculate_formula(company, from_date, to_date)

        return self.get_account_total(company, from_date, to_date)

    def get_account_total(self, company, from_date, to_date):
        """Get total from mapped MOF accounts"""
        if not self.mof_accounts:
            return 0.0

        total = 0.0
        for row in self.mof_accounts:
            if row.mof_account and row.enabled:
                # Get balance from MOF Account Mapping
                if frappe.db.exists("MOF Account Mapping", row.mof_account):
                    mapping = frappe.get_doc("MOF Account Mapping", row.mof_account)
                    balance = mapping.get_balance(company, from_date, to_date)
                    total += balance * (row.weight or 1.0)

        return total

    def calculate_formula(self, company, from_date, to_date):
        """Calculate value from formula referencing other rows"""
        if not self.calculation_formula:
            return 0.0

        formula = self.calculation_formula

        # Find all row references
        pattern = r'(СБТ|ОҮТ|МГТ|ӨМТ|SBT|OUT|MGT|OMT)\.\d+(\.\d+)*'
        re.findall(pattern, formula, re.IGNORECASE)

        # Build full references list
        full_refs = re.findall(r'((?:СБТ|ОҮТ|МГТ|ӨМТ|SBT|OUT|MGT|OMT)\.\d+(?:\.\d+)*)',
                               formula, re.IGNORECASE)

        # Get values for each reference
        values = {}
        for ref in full_refs:
            row_name = f"{self.form_code}-{ref}"
            if frappe.db.exists("MOF Report Form Row", row_name):
                row = frappe.get_doc("MOF Report Form Row", row_name)
                values[ref] = row.calculate_row_value(company, from_date, to_date)
            else:
                values[ref] = 0.0

        # Replace references with values in formula
        eval_formula = formula
        for ref, value in sorted(values.items(), key=lambda x: -len(x[0])):
            eval_formula = eval_formula.replace(ref, str(value))

        # Evaluate formula safely
        try:
            # Only allow basic math operations
            allowed_chars = set('0123456789.+-*/() ')
            if not all(c in allowed_chars for c in eval_formula):
                return 0.0

            result = eval(eval_formula)  # nosec - validated input
            return float(result)
        except Exception:
            frappe.log_error(
                f"Formula evaluation error: {self.calculation_formula}",
                "MOF Report Form Row"
            )
            return 0.0


# Child table for MOF account references
class MOFReportFormRowAccount(Document):
    """Child table for MOF account codes in form row"""
    pass
