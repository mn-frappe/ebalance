# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

import frappe
from frappe.model.document import Document


class eBalanceReportPeriod(Document):
	"""eBalance Report Period - Synced from eBalance API"""

	def validate(self):
		self._parse_period_code()

	def _parse_period_code(self):
		"""Parse period code to extract type and year"""
		if not self.period_code:
			return

		code = self.period_code

		# Parse period type from code
		# Examples: End_2024_H_2, SubEnd_2024_M_1, Open_2025_M_2, Summary_2024_H_2
		if code.startswith("End_"):
			self.period_type = "Annual"
		elif code.startswith("SubEnd_"):
			self.period_type = "Semi-Annual"
		elif code.startswith("Open_"):
			self.period_type = "Opening"
		elif code.startswith("Summary"):
			self.period_type = "Summary"

		# Try to extract year
		parts = code.split("_")
		for part in parts:
			if part.isdigit() and len(part) == 4:
				# Link to fiscal year if exists
				if frappe.db.exists("Fiscal Year", part):
					self.fiscal_year = part
				break
