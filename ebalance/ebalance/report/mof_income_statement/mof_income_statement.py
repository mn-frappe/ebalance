# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
MOF Income Statement (ОҮТ) Report

Generates Income Statement (Орлогын үр дүнгийн тайлан) in MOF format
using Mongolian Standard Chart of Accounts (НББОУС) mapping.

This report transforms ERPNext GL Entry data into the standard MOF format
required for eBalance submission.
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    """
    Execute MOF Income Statement report.

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
            "fieldname": "amount",
            "label": _("Amount"),
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
    """Generate Income Statement data from MOF Account Mappings"""
    data = []

    # Get date range
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.company

    if filters.fiscal_year and not (from_date and to_date):
        fy = frappe.get_doc("Fiscal Year", filters.fiscal_year)
        from_date = fy.year_start_date
        to_date = fy.year_end_date

    # Income Statement structure (ОҮТ - Орлогын үр дүнгийн тайлан)
    is_structure = [
        # Revenue (Орлого)
        {"row_code": "ОҮТ.1", "account_name_mn": "НИЙТ ОРЛОГО", "account_name": "TOTAL REVENUE", "is_total": True, "indent": 0},
        {"row_code": "ОҮТ.1.1", "account_name_mn": "Борлуулалтын орлого", "account_name": "Sales revenue", "indent": 1, "mof_codes": ["4100", "4110", "4120", "4130"]},
        {"row_code": "ОҮТ.1.2", "account_name_mn": "Үйлчилгээний орлого", "account_name": "Service revenue", "indent": 1, "mof_codes": ["4200", "4210", "4220"]},
        {"row_code": "ОҮТ.1.3", "account_name_mn": "Бусад үйл ажиллагааны орлого", "account_name": "Other operating income", "indent": 1, "mof_codes": ["4300", "4310", "4320", "4330", "4400"]},

        # Cost of Sales (Борлуулсан бүтээгдэхүүний өртөг)
        {"row_code": "ОҮТ.2", "account_name_mn": "БОРЛУУЛСАН БҮТЭЭГДЭХҮҮНИЙ ӨРТӨГ", "account_name": "COST OF GOODS SOLD", "is_total": True, "indent": 0},
        {"row_code": "ОҮТ.2.1", "account_name_mn": "Борлуулалтын өртөг", "account_name": "Cost of sales", "indent": 1, "mof_codes": ["5100", "5110", "5120", "5130"]},
        {"row_code": "ОҮТ.2.2", "account_name_mn": "Үйлчилгээний өртөг", "account_name": "Cost of services", "indent": 1, "mof_codes": ["5200", "5210", "5220"]},
        {"row_code": "ОҮТ.2.3", "account_name_mn": "Бусад өртөг", "account_name": "Other costs", "indent": 1, "mof_codes": ["5300", "5400", "5500"]},

        # Gross Profit
        {"row_code": "ОҮТ.3", "account_name_mn": "НИЙТ АШИГ", "account_name": "GROSS PROFIT", "is_total": True, "indent": 0, "calculated": True},

        # Operating Expenses (Үйл ажиллагааны зардал)
        {"row_code": "ОҮТ.4", "account_name_mn": "ҮЙЛ АЖИЛЛАГААНЫ ЗАРДАЛ", "account_name": "OPERATING EXPENSES", "is_total": True, "indent": 0},
        {"row_code": "ОҮТ.4.1", "account_name_mn": "Борлуулалтын зардал", "account_name": "Distribution costs", "indent": 1, "mof_codes": ["6100", "6110", "6120", "6130", "6140", "6150", "6160"]},
        {"row_code": "ОҮТ.4.2", "account_name_mn": "Удирдлагын зардал", "account_name": "Administrative expenses", "indent": 1, "mof_codes": ["6200", "6210", "6220", "6230", "6240", "6250", "6260", "6270", "6280", "6290"]},
        {"row_code": "ОҮТ.4.3", "account_name_mn": "Цалин хөлс", "account_name": "Salaries and wages", "indent": 1, "mof_codes": ["6300", "6310", "6320", "6330", "6340"]},
        {"row_code": "ОҮТ.4.4", "account_name_mn": "Элэгдлийн зардал", "account_name": "Depreciation", "indent": 1, "mof_codes": ["6400", "6410", "6420"]},
        {"row_code": "ОҮТ.4.5", "account_name_mn": "Бусад үйл ажиллагааны зардал", "account_name": "Other operating expenses", "indent": 1, "mof_codes": ["6500", "6510", "6520", "6530", "6600", "6700", "6800", "6900"]},

        # Operating Profit
        {"row_code": "ОҮТ.5", "account_name_mn": "ҮЙЛ АЖИЛЛАГААНЫ АШИГ", "account_name": "OPERATING PROFIT", "is_total": True, "indent": 0, "calculated": True},

        # Finance Income/Expense (Санхүүгийн орлого/зардал)
        {"row_code": "ОҮТ.6", "account_name_mn": "САНХҮҮГИЙН ОРЛОГО/ЗАРДАЛ", "account_name": "FINANCE INCOME/EXPENSE", "is_total": True, "indent": 0},
        {"row_code": "ОҮТ.6.1", "account_name_mn": "Хүүгийн орлого", "account_name": "Interest income", "indent": 1, "mof_codes": ["7100", "7110"]},
        {"row_code": "ОҮТ.6.2", "account_name_mn": "Ногдол ашгийн орлого", "account_name": "Dividend income", "indent": 1, "mof_codes": ["7120", "7130"]},
        {"row_code": "ОҮТ.6.3", "account_name_mn": "Валютын ханшийн зөрүү", "account_name": "Foreign exchange gain/loss", "indent": 1, "mof_codes": ["7200", "7210"]},
        {"row_code": "ОҮТ.6.4", "account_name_mn": "Хүүгийн зардал", "account_name": "Interest expense", "indent": 1, "mof_codes": ["7300", "7310", "7320"]},
        {"row_code": "ОҮТ.6.5", "account_name_mn": "Бусад санхүүгийн зардал", "account_name": "Other finance costs", "indent": 1, "mof_codes": ["7400", "7500", "7600", "7700", "7800", "7900"]},

        # Other Income/Expense (Бусад орлого/зардал)
        {"row_code": "ОҮТ.7", "account_name_mn": "БУСАД ОРЛОГО/ЗАРДАЛ", "account_name": "OTHER INCOME/EXPENSE", "is_total": True, "indent": 0},
        {"row_code": "ОҮТ.7.1", "account_name_mn": "Бусад орлого", "account_name": "Other income", "indent": 1, "mof_codes": ["8100", "8110", "8120", "8130", "8140", "8150"]},
        {"row_code": "ОҮТ.7.2", "account_name_mn": "Бусад зардал", "account_name": "Other expenses", "indent": 1, "mof_codes": ["8200", "8210", "8220", "8230", "8240"]},

        # Profit Before Tax
        {"row_code": "ОҮТ.8", "account_name_mn": "ТАТВАРЫН ӨМНӨХ АШИГ", "account_name": "PROFIT BEFORE TAX", "is_total": True, "indent": 0, "calculated": True},

        # Income Tax (Татвар)
        {"row_code": "ОҮТ.9", "account_name_mn": "ОРЛОГЫН ТАТВАР", "account_name": "INCOME TAX", "is_total": True, "indent": 0},
        {"row_code": "ОҮТ.9.1", "account_name_mn": "Тайлант үеийн татвар", "account_name": "Current tax expense", "indent": 1, "mof_codes": ["9100", "9110", "9120"]},
        {"row_code": "ОҮТ.9.2", "account_name_mn": "Хойшлогдсон татвар", "account_name": "Deferred tax", "indent": 1, "mof_codes": ["9200", "9210", "9220"]},

        # Net Profit
        {"row_code": "ОҮТ.10", "account_name_mn": "ЦЭВЭР АШИГ", "account_name": "NET PROFIT", "is_total": True, "indent": 0, "calculated": True}
    ]

    # Calculate balances
    balances = {}

    for row in is_structure:
        if row.get("mof_codes"):
            amount = get_mof_account_balance(
                company, from_date, to_date, row["mof_codes"]
            )
            balances[row["row_code"]] = amount

    # Calculate totals
    balances["ОҮТ.1"] = sum(balances.get(f"ОҮТ.1.{i}", 0) for i in range(1, 4))
    balances["ОҮТ.2"] = sum(balances.get(f"ОҮТ.2.{i}", 0) for i in range(1, 4))
    balances["ОҮТ.3"] = balances.get("ОҮТ.1", 0) - balances.get("ОҮТ.2", 0)  # Gross Profit

    balances["ОҮТ.4"] = sum(balances.get(f"ОҮТ.4.{i}", 0) for i in range(1, 6))
    balances["ОҮТ.5"] = balances.get("ОҮТ.3", 0) - balances.get("ОҮТ.4", 0)  # Operating Profit

    balances["ОҮТ.6"] = sum(balances.get(f"ОҮТ.6.{i}", 0) for i in range(1, 6))
    balances["ОҮТ.7"] = balances.get("ОҮТ.7.1", 0) - balances.get("ОҮТ.7.2", 0)

    balances["ОҮТ.8"] = balances.get("ОҮТ.5", 0) + balances.get("ОҮТ.6", 0) + balances.get("ОҮТ.7", 0)  # PBT
    balances["ОҮТ.9"] = sum(balances.get(f"ОҮТ.9.{i}", 0) for i in range(1, 3))
    balances["ОҮТ.10"] = balances.get("ОҮТ.8", 0) - balances.get("ОҮТ.9", 0)  # Net Profit

    # Build report data
    for row in is_structure:
        data.append({
            "row_code": row["row_code"],
            "account_name_mn": row["account_name_mn"],
            "account_name": row["account_name"],
            "amount": flt(balances.get(row["row_code"], 0), 2),
            "indent": row.get("indent", 0),
            "is_total": row.get("is_total", False)
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
    total_revenue = 0
    total_expenses = 0
    net_profit = 0

    for row in data:
        if row.get("row_code") == "ОҮТ.1":
            total_revenue = row.get("amount", 0)
        elif row.get("row_code") == "ОҮТ.4":
            total_expenses = row.get("amount", 0)
        elif row.get("row_code") == "ОҮТ.10":
            net_profit = row.get("amount", 0)

    return [
        {
            "value": total_revenue,
            "label": _("Total Revenue"),
            "datatype": "Currency",
            "currency": frappe.db.get_default("currency")
        },
        {
            "value": total_expenses,
            "label": _("Total Expenses"),
            "datatype": "Currency",
            "currency": frappe.db.get_default("currency")
        },
        {
            "value": net_profit,
            "label": _("Net Profit"),
            "datatype": "Currency",
            "currency": frappe.db.get_default("currency"),
            "indicator": "Green" if net_profit >= 0 else "Red"
        }
    ]


def get_chart_data(data):
    """Generate chart data"""
    total_revenue = 0
    cogs = 0
    opex = 0
    net_profit = 0

    for row in data:
        if row.get("row_code") == "ОҮТ.1":
            total_revenue = row.get("amount", 0)
        elif row.get("row_code") == "ОҮТ.2":
            cogs = row.get("amount", 0)
        elif row.get("row_code") == "ОҮТ.4":
            opex = row.get("amount", 0)
        elif row.get("row_code") == "ОҮТ.10":
            net_profit = row.get("amount", 0)

    return {
        "data": {
            "labels": [_("Revenue"), _("COGS"), _("Operating Exp"), _("Net Profit")],
            "datasets": [
                {
                    "name": _("Income Statement"),
                    "values": [total_revenue, cogs, opex, net_profit]
                }
            ]
        },
        "type": "bar",
        "colors": ["#5e64ff", "#ff5858", "#ffbb00", "#29cd42"]
    }
