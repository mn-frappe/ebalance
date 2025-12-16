# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
MOF Account Fixtures

Provides 154 standard Mongolian Chart of Accounts (НББОУС) entries
based on mn_chart.csv for automatic import during eBalance installation.

Account Structure:
- 1xxx: Assets (Хөрөнгө) - 55 accounts
- 2xxx: Liabilities (Өр төлбөр) - 29 accounts  
- 3xxx: Equity (Өмч) - 12 accounts
- 4xxx: Revenue (Орлого) - 15 accounts
- 5xxx: Cost of Sales (Борлуулалтын өртөг) - 5 accounts
- 6xxx: Operating Expenses (Үйл ажиллагааны зардал) - 22 accounts
- 7xxx: Finance Costs (Санхүүгийн зардал) - 4 accounts
- 8xxx: Other Expenses (Бусад зардал) - 4 accounts
- 9xxx: Tax & Off-balance (Татвар, тэнцлийн гаднах) - 8 accounts
"""

import frappe
from frappe import _


# Complete Mongolian Standard Chart of Accounts (154 accounts)
MOF_ACCOUNTS = [
	# ============================================
	# 1xxx - ASSETS (ХӨРӨНГӨ)
	# ============================================
	{"mof_account_number": "1000", "mof_account_name": "Assets", "mof_account_name_mn": "Хөрөнгө", "parent_mof_account": None, "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1100", "mof_account_name": "Current assets", "mof_account_name_mn": "Эргэлтийн хөрөнгө", "parent_mof_account": "1000", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1110", "mof_account_name": "Cash and cash equivalents", "mof_account_name_mn": "Мөнгө, түүнтэй адилтгах хөрөнгө", "parent_mof_account": "1100", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1111", "mof_account_name": "Cash on hand", "mof_account_name_mn": "Кассан дахь бэлэн мөнгө", "parent_mof_account": "1110", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1112", "mof_account_name": "Bank current accounts - MNT", "mof_account_name_mn": "Банк дахь харилцах данс - төгрөг", "parent_mof_account": "1110", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1113", "mof_account_name": "Bank current accounts - foreign currency", "mof_account_name_mn": "Банк дахь харилцах данс - гадаад валют", "parent_mof_account": "1110", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1114", "mof_account_name": "Restricted cash", "mof_account_name_mn": "Хязгаарлагдсан бэлэн мөнгө", "parent_mof_account": "1110", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1120", "mof_account_name": "Short-term deposits", "mof_account_name_mn": "Богино хугацаат хадгаламж", "parent_mof_account": "1100", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1200", "mof_account_name": "Trade and other receivables", "mof_account_name_mn": "Авлага ба бусад авлага", "parent_mof_account": "1100", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1201", "mof_account_name": "Trade receivables - domestic", "mof_account_name_mn": "Дотоодын харилцагчаас авах авлага", "parent_mof_account": "1200", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1202", "mof_account_name": "Trade receivables - foreign", "mof_account_name_mn": "Гадаадын харилцагчаас авах авлага", "parent_mof_account": "1200", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1203", "mof_account_name": "Notes receivable", "mof_account_name_mn": "Векселиэр авах авлага", "parent_mof_account": "1200", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1204", "mof_account_name": "Receivables from employees", "mof_account_name_mn": "Ажилтнуудаас авах авлага", "parent_mof_account": "1200", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1205", "mof_account_name": "Allowance for doubtful receivables", "mof_account_name_mn": "Авлагын үнэ цэнийн бууралтын нөөц", "parent_mof_account": "1200", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1300", "mof_account_name": "Inventories", "mof_account_name_mn": "Бараа материал", "parent_mof_account": "1100", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1301", "mof_account_name": "Raw materials and supplies", "mof_account_name_mn": "Түүхий эд, материал", "parent_mof_account": "1300", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1302", "mof_account_name": "Work in progress", "mof_account_name_mn": "Дуусаагүй үйлдвэрлэл", "parent_mof_account": "1300", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1303", "mof_account_name": "Finished goods", "mof_account_name_mn": "Бэлэн бүтээгдэхүүн", "parent_mof_account": "1300", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1304", "mof_account_name": "Merchandise", "mof_account_name_mn": "Бараа бүтээгдэхүүн", "parent_mof_account": "1300", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1305", "mof_account_name": "Goods in transit", "mof_account_name_mn": "Замд байгаа бараа материал", "parent_mof_account": "1300", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1306", "mof_account_name": "Inventory write-down allowance", "mof_account_name_mn": "Бараа материалын үнэ цэнийн бууралтын нөөц", "parent_mof_account": "1300", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1400", "mof_account_name": "Other current assets", "mof_account_name_mn": "Бусад эргэлтийн хөрөнгө", "parent_mof_account": "1100", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1410", "mof_account_name": "Short-term financial investments", "mof_account_name_mn": "Богино хугацаат санхүүгийн хөрөнгө", "parent_mof_account": "1400", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1420", "mof_account_name": "Short-term loans issued", "mof_account_name_mn": "Богино хугацаат зээл олгосон", "parent_mof_account": "1400", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1430", "mof_account_name": "VAT receivable", "mof_account_name_mn": "НӨАТ-ын авлага", "parent_mof_account": "1400", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1440", "mof_account_name": "Excise tax receivable", "mof_account_name_mn": "Онцгой албан татварын авлага", "parent_mof_account": "1400", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1450", "mof_account_name": "Other tax receivable", "mof_account_name_mn": "Бусад татварын авлага", "parent_mof_account": "1400", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1460", "mof_account_name": "Prepaid expenses", "mof_account_name_mn": "Урьдчилж төлсөн зардал", "parent_mof_account": "1400", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1470", "mof_account_name": "Advances paid to suppliers", "mof_account_name_mn": "Нийлүүлэгчид өгсөн урьдчилгаа", "parent_mof_account": "1400", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1500", "mof_account_name": "Non-current assets held for sale", "mof_account_name_mn": "Борлуулж байгаа зорилгоор эзэмшиж буй эргэлтийн бус хөрөнгө", "parent_mof_account": "1100", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1600", "mof_account_name": "Biological assets - current", "mof_account_name_mn": "Биологийн хөрөнгө - богино хугацаат", "parent_mof_account": "1100", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1700", "mof_account_name": "Other current assets - miscellaneous", "mof_account_name_mn": "Бусад эргэлтийн хөрөнгө (ангилагдаагүй)", "parent_mof_account": "1100", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1800", "mof_account_name": "Property, plant and equipment", "mof_account_name_mn": "Үндсэн хөрөнгө", "parent_mof_account": "1000", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1801", "mof_account_name": "Land", "mof_account_name_mn": "Газрын үндсэн хөрөнгө", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1802", "mof_account_name": "Buildings and structures", "mof_account_name_mn": "Барилга, байгууламж", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1803", "mof_account_name": "Machinery and equipment", "mof_account_name_mn": "Машин, тоног төхөөрөмж", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1804", "mof_account_name": "Vehicles", "mof_account_name_mn": "Тээврийн хэрэгсэл", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1805", "mof_account_name": "Mining and specialized equipment", "mof_account_name_mn": "Уул уурхайн болон тусгай тоног төхөөрөмж", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1810", "mof_account_name": "Construction in progress", "mof_account_name_mn": "Баригдаж буй барилга байгууламж", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1820", "mof_account_name": "Accumulated depreciation - buildings", "mof_account_name_mn": "Үндсэн хөрөнгийн хуримтлагдсан элэгдэл - барилга", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1821", "mof_account_name": "Accumulated depreciation - machinery and equipment", "mof_account_name_mn": "Үндсэн хөрөнгийн хуримтлагдсан элэгдэл - машин, тоног төхөөрөмж", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1822", "mof_account_name": "Accumulated depreciation - vehicles", "mof_account_name_mn": "Үндсэн хөрөнгийн хуримтлагдсан элэгдэл - тээврийн хэрэгсэл", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1829", "mof_account_name": "Accumulated depreciation - other PPE", "mof_account_name_mn": "Үндсэн хөрөнгийн хуримтлагдсан элэгдэл - бусад", "parent_mof_account": "1800", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1900", "mof_account_name": "Intangible assets", "mof_account_name_mn": "Биет бус хөрөнгө", "parent_mof_account": "1000", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1901", "mof_account_name": "Software", "mof_account_name_mn": "Программ хангамж", "parent_mof_account": "1900", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1902", "mof_account_name": "Licenses and rights", "mof_account_name_mn": "Лиценз, эрх", "parent_mof_account": "1900", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1903", "mof_account_name": "Goodwill", "mof_account_name_mn": "Гүүдвилл", "parent_mof_account": "1900", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1910", "mof_account_name": "Accumulated amortization of intangibles", "mof_account_name_mn": "Биет бус хөрөнгийн хуримтлагдсан элэгдэл", "parent_mof_account": "1900", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1950", "mof_account_name": "Long-term financial investments", "mof_account_name_mn": "Урт хугацаат санхүүгийн хөрөнгө", "parent_mof_account": "1000", "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "1951", "mof_account_name": "Long-term equity investments", "mof_account_name_mn": "Урт хугацаат хөрөнгө оруулалт - хувьцаа", "parent_mof_account": "1950", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1952", "mof_account_name": "Long-term debt instruments", "mof_account_name_mn": "Урт хугацаат хөрөнгө оруулалт - өрийн хэрэгсэл", "parent_mof_account": "1950", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1960", "mof_account_name": "Long-term loans issued", "mof_account_name_mn": "Урт хугацаат зээл олгосон", "parent_mof_account": "1000", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1970", "mof_account_name": "Biological assets - non-current", "mof_account_name_mn": "Биологийн хөрөнгө - урт хугацаат", "parent_mof_account": "1000", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1980", "mof_account_name": "Deferred tax asset", "mof_account_name_mn": "Хойшлогдсон татварын хөрөнгө", "parent_mof_account": "1000", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "1990", "mof_account_name": "Other non-current assets", "mof_account_name_mn": "Бусад эргэлтийн бус хөрөнгө", "parent_mof_account": "1000", "is_group": 0, "root_type": "Asset"},
	
	# ============================================
	# 2xxx - LIABILITIES (ӨР ТӨЛБӨР)
	# ============================================
	{"mof_account_number": "2000", "mof_account_name": "Liabilities", "mof_account_name_mn": "Өр төлбөр", "parent_mof_account": None, "is_group": 1, "root_type": "Liability"},
	{"mof_account_number": "2100", "mof_account_name": "Current liabilities", "mof_account_name_mn": "Богино хугацаат өр төлбөр", "parent_mof_account": "2000", "is_group": 1, "root_type": "Liability"},
	{"mof_account_number": "2110", "mof_account_name": "Trade payables", "mof_account_name_mn": "Нийлүүлэгчдэд өгөх өр", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2120", "mof_account_name": "Short-term bank loans", "mof_account_name_mn": "Богино хугацаат банкны зээл", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2130", "mof_account_name": "Current portion of long-term loans", "mof_account_name_mn": "Урт хугацаат зээлийн богино хугацаат хэсэг", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2140", "mof_account_name": "Short-term borrowings from related parties", "mof_account_name_mn": "Холбогдох этгээдээс авсан богино хугацаат зээл", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2150", "mof_account_name": "Advances received from customers", "mof_account_name_mn": "Харилцагчаас авсан урьдчилгаа", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2160", "mof_account_name": "Salaries and wages payable", "mof_account_name_mn": "Ажилчдын цалин хөлсний өглөг", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2170", "mof_account_name": "Social insurance payable", "mof_account_name_mn": "Нийгмийн даатгалын шимтгэлийн өглөг", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2180", "mof_account_name": "Personal income tax payable", "mof_account_name_mn": "Хувийн орлогын албан татварын өглөг", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2190", "mof_account_name": "Other payables", "mof_account_name_mn": "Бусад өглөг", "parent_mof_account": "2100", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2200", "mof_account_name": "Taxes payable", "mof_account_name_mn": "Татварын өглөг", "parent_mof_account": "2100", "is_group": 1, "root_type": "Liability"},
	{"mof_account_number": "2210", "mof_account_name": "VAT payable", "mof_account_name_mn": "НӨАТ-ын өглөг", "parent_mof_account": "2200", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2220", "mof_account_name": "Excise tax payable", "mof_account_name_mn": "Онцгой албан татварын өглөг", "parent_mof_account": "2200", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2230", "mof_account_name": "Corporate income tax payable", "mof_account_name_mn": "Аж ахуйн нэгжийн орлогын албан татварын өглөг", "parent_mof_account": "2200", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2240", "mof_account_name": "Customs duties payable", "mof_account_name_mn": "Гаалийн албан татварын өглөг", "parent_mof_account": "2200", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2250", "mof_account_name": "Environmental fees payable", "mof_account_name_mn": "Байгаль орчны төлбөрийн өглөг", "parent_mof_account": "2200", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2300", "mof_account_name": "Provisions - current", "mof_account_name_mn": "Резерв ба түр хугацаат үүрэг", "parent_mof_account": "2100", "is_group": 1, "root_type": "Liability"},
	{"mof_account_number": "2310", "mof_account_name": "Provision for bonuses and unused vacations", "mof_account_name_mn": "Шагнал, амралтын мөнгөний нөөц", "parent_mof_account": "2300", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2320", "mof_account_name": "Provision for warranty obligations", "mof_account_name_mn": "Баталгаат засварын нөөц", "parent_mof_account": "2300", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2330", "mof_account_name": "Provision for taxes and penalties", "mof_account_name_mn": "Татвар, торгуулийн нөөц", "parent_mof_account": "2300", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2400", "mof_account_name": "Non-current liabilities", "mof_account_name_mn": "Урт хугацаат өр төлбөр", "parent_mof_account": "2000", "is_group": 1, "root_type": "Liability"},
	{"mof_account_number": "2410", "mof_account_name": "Long-term bank loans", "mof_account_name_mn": "Урт хугацаат банкны зээл", "parent_mof_account": "2400", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2420", "mof_account_name": "Bonds issued", "mof_account_name_mn": "Гаргасан бонд", "parent_mof_account": "2400", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2430", "mof_account_name": "Lease liabilities", "mof_account_name_mn": "Түрээсийн өр төлбөр", "parent_mof_account": "2400", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2440", "mof_account_name": "Long-term borrowings from related parties", "mof_account_name_mn": "Холбогдох этгээдээс авсан урт хугацаат зээл", "parent_mof_account": "2400", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2450", "mof_account_name": "Deferred tax liability", "mof_account_name_mn": "Хойшлогдсон татварын өр төлбөр", "parent_mof_account": "2400", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2460", "mof_account_name": "Asset retirement / decommissioning obligation", "mof_account_name_mn": "Үндсэн хөрөнгө буулгалтын нөөц, нөхөн сэргээлтийн үүрэг", "parent_mof_account": "2400", "is_group": 0, "root_type": "Liability"},
	{"mof_account_number": "2490", "mof_account_name": "Other non-current liabilities", "mof_account_name_mn": "Бусад урт хугацаат өр төлбөр", "parent_mof_account": "2400", "is_group": 0, "root_type": "Liability"},
	
	# ============================================
	# 3xxx - EQUITY (ӨМЧ)
	# ============================================
	{"mof_account_number": "3000", "mof_account_name": "Equity", "mof_account_name_mn": "Өмч", "parent_mof_account": None, "is_group": 1, "root_type": "Equity"},
	{"mof_account_number": "3100", "mof_account_name": "Share capital", "mof_account_name_mn": "Хувь нийлүүлсэн хөрөнгө", "parent_mof_account": "3000", "is_group": 1, "root_type": "Equity"},
	{"mof_account_number": "3110", "mof_account_name": "Ordinary share capital", "mof_account_name_mn": "Энгийн хувьцааны хөрөнгө", "parent_mof_account": "3100", "is_group": 0, "root_type": "Equity"},
	{"mof_account_number": "3120", "mof_account_name": "Preferred share capital", "mof_account_name_mn": "Давуу эрхтэй хувьцааны хөрөнгө", "parent_mof_account": "3100", "is_group": 0, "root_type": "Equity"},
	{"mof_account_number": "3200", "mof_account_name": "Additional paid-in capital", "mof_account_name_mn": "Давхардуулан төлсөн хөрөнгө", "parent_mof_account": "3000", "is_group": 0, "root_type": "Equity"},
	{"mof_account_number": "3300", "mof_account_name": "Retained earnings (accumulated profit/loss)", "mof_account_name_mn": "Хуримтлагдсан ашиг (алдагдал)", "parent_mof_account": "3000", "is_group": 1, "root_type": "Equity"},
	{"mof_account_number": "3310", "mof_account_name": "Current year profit (loss)", "mof_account_name_mn": "Тайлант жилийн ашиг (алдагдал)", "parent_mof_account": "3300", "is_group": 0, "root_type": "Equity"},
	{"mof_account_number": "3400", "mof_account_name": "Reserve capital", "mof_account_name_mn": "Нөөцийн сан", "parent_mof_account": "3000", "is_group": 1, "root_type": "Equity"},
	{"mof_account_number": "3410", "mof_account_name": "Legal reserve", "mof_account_name_mn": "Хуулийн дагуу үүсгэсэн нөөц", "parent_mof_account": "3400", "is_group": 0, "root_type": "Equity"},
	{"mof_account_number": "3420", "mof_account_name": "Other reserves", "mof_account_name_mn": "Бусад нөөцийн сан", "parent_mof_account": "3400", "is_group": 0, "root_type": "Equity"},
	{"mof_account_number": "3500", "mof_account_name": "Treasury shares", "mof_account_name_mn": "Дахин худалдаж авсан хувьцаа", "parent_mof_account": "3000", "is_group": 0, "root_type": "Equity"},
	{"mof_account_number": "3600", "mof_account_name": "Non-controlling interest", "mof_account_name_mn": "Хяналтын бус сонирхол", "parent_mof_account": "3000", "is_group": 0, "root_type": "Equity"},
	
	# ============================================
	# 4xxx - REVENUE / INCOME (ОРЛОГО)
	# ============================================
	{"mof_account_number": "4000", "mof_account_name": "Revenue and gains", "mof_account_name_mn": "Орлого ба олз", "parent_mof_account": None, "is_group": 1, "root_type": "Income"},
	{"mof_account_number": "4100", "mof_account_name": "Sales revenue - goods subject to excise tax", "mof_account_name_mn": "Борлуулалтын орлого - онцгой албан татвартай бараа", "parent_mof_account": "4000", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4110", "mof_account_name": "Sales revenue - other goods", "mof_account_name_mn": "Борлуулалтын орлого - бусад бараа", "parent_mof_account": "4000", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4120", "mof_account_name": "Service revenue", "mof_account_name_mn": "Үйлчилгээний орлого", "parent_mof_account": "4000", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4130", "mof_account_name": "Export sales revenue", "mof_account_name_mn": "Экспортын борлуулалтын орлого", "parent_mof_account": "4000", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4140", "mof_account_name": "Domestic sales revenue", "mof_account_name_mn": "Дотоодын борлуулалтын орлого", "parent_mof_account": "4000", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4200", "mof_account_name": "Other operating income", "mof_account_name_mn": "Үйл ажиллагааны бусад орлого", "parent_mof_account": "4000", "is_group": 1, "root_type": "Income"},
	{"mof_account_number": "4210", "mof_account_name": "Income from subsidies and grants", "mof_account_name_mn": "Татаас, буцалтгүй тусламжийн орлого", "parent_mof_account": "4200", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4220", "mof_account_name": "Income from disposal of PPE", "mof_account_name_mn": "Үндсэн хөрөнгө борлуулалтын олз", "parent_mof_account": "4200", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4230", "mof_account_name": "Income from penalties and fines", "mof_account_name_mn": "Торгууль, алдангийн орлого", "parent_mof_account": "4200", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4300", "mof_account_name": "Finance income", "mof_account_name_mn": "Санхүүгийн орлого", "parent_mof_account": "4000", "is_group": 1, "root_type": "Income"},
	{"mof_account_number": "4310", "mof_account_name": "Interest income", "mof_account_name_mn": "Хүүгийн орлого", "parent_mof_account": "4300", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4320", "mof_account_name": "Foreign exchange gain", "mof_account_name_mn": "Валютын ханшийн зөрүүгийн ашиг", "parent_mof_account": "4300", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4330", "mof_account_name": "Gain from fair value remeasurement", "mof_account_name_mn": "Хөрөнгийн үнэлгээний олз", "parent_mof_account": "4300", "is_group": 0, "root_type": "Income"},
	{"mof_account_number": "4400", "mof_account_name": "Other non-operating income", "mof_account_name_mn": "Бусад үйл ажиллагааны бус орлого", "parent_mof_account": "4000", "is_group": 0, "root_type": "Income"},
	
	# ============================================
	# 5xxx - COST OF SALES (БОРЛУУЛАЛТЫН ӨРТӨГ)
	# ============================================
	{"mof_account_number": "5000", "mof_account_name": "Cost of sales", "mof_account_name_mn": "Борлуулалтын өртөг", "parent_mof_account": None, "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "5100", "mof_account_name": "Cost of goods sold - excise goods", "mof_account_name_mn": "Борлуулсан онцгой албан татвартай барааны өртөг", "parent_mof_account": "5000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "5110", "mof_account_name": "Cost of goods sold - other goods", "mof_account_name_mn": "Борлуулсан бусад барааны өртөг", "parent_mof_account": "5000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "5120", "mof_account_name": "Cost of services rendered", "mof_account_name_mn": "Үйлчилгээ үзүүлэхэд гарсан өртөг", "parent_mof_account": "5000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "5130", "mof_account_name": "Cost of goods for resale", "mof_account_name_mn": "Дахин борлуулах барааны өртөг", "parent_mof_account": "5000", "is_group": 0, "root_type": "Expense"},
	
	# ============================================
	# 6xxx - OPERATING EXPENSES (ҮЙЛ АЖИЛЛАГААНЫ ЗАРДАЛ)
	# ============================================
	{"mof_account_number": "6000", "mof_account_name": "Operating expenses", "mof_account_name_mn": "Үйл ажиллагааны зардал", "parent_mof_account": None, "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "6100", "mof_account_name": "Selling and distribution expenses", "mof_account_name_mn": "Борлуулалт, түгээлтийн зардал", "parent_mof_account": "6000", "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "6110", "mof_account_name": "Advertising and marketing expenses", "mof_account_name_mn": "Сурталчилгаа, маркетингийн зардал", "parent_mof_account": "6100", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6120", "mof_account_name": "Transportation and logistics expenses", "mof_account_name_mn": "Тээвэр, ложистикийн зардал", "parent_mof_account": "6100", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6130", "mof_account_name": "Sales staff salaries", "mof_account_name_mn": "Борлуулалтын ажилтнуудын цалин", "parent_mof_account": "6100", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6200", "mof_account_name": "General and administrative expenses", "mof_account_name_mn": "Ерөнхий ба удирдлагын зардал", "parent_mof_account": "6000", "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "6210", "mof_account_name": "Office salaries and wages", "mof_account_name_mn": "Оффисын ажилчдын цалин хөлс", "parent_mof_account": "6200", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6220", "mof_account_name": "Social insurance expense", "mof_account_name_mn": "Нийгмийн даатгалын зардал", "parent_mof_account": "6200", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6230", "mof_account_name": "Office rent expense", "mof_account_name_mn": "Оффисын түрээсийн зардал", "parent_mof_account": "6200", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6240", "mof_account_name": "Utilities expense", "mof_account_name_mn": "Коммуналын зардал", "parent_mof_account": "6200", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6250", "mof_account_name": "Business travel expense", "mof_account_name_mn": "Томилолтын зардал", "parent_mof_account": "6200", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6260", "mof_account_name": "Professional services fees", "mof_account_name_mn": "Мэргэжлийн үйлчилгээний хөлс", "parent_mof_account": "6200", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6300", "mof_account_name": "Depreciation and amortization expense", "mof_account_name_mn": "Элэгдэл, хорогдлын зардал", "parent_mof_account": "6000", "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "6310", "mof_account_name": "Depreciation of property plant and equipment", "mof_account_name_mn": "Үндсэн хөрөнгийн элэгдлийн зардал", "parent_mof_account": "6300", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6320", "mof_account_name": "Amortization of intangible assets", "mof_account_name_mn": "Биет бус хөрөнгийн элэгдлийн зардал", "parent_mof_account": "6300", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6400", "mof_account_name": "Taxes other than income and excise", "mof_account_name_mn": "Орлогын ба онцгой албан татвараас бусад татварын зардал", "parent_mof_account": "6000", "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "6410", "mof_account_name": "Property tax expense", "mof_account_name_mn": "Хөрөнгийн татварын зардал", "parent_mof_account": "6400", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6420", "mof_account_name": "Road vehicle and other fees", "mof_account_name_mn": "Авто зам, тээврийн хэрэгслийн болон бусад хураамж", "parent_mof_account": "6400", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6500", "mof_account_name": "Repairs and maintenance expense", "mof_account_name_mn": "Засвар, үйлчилгээний зардал", "parent_mof_account": "6000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6600", "mof_account_name": "Bad debt expense", "mof_account_name_mn": "Авлагын хугацаа хэтэрсний алдагдал", "parent_mof_account": "6000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6700", "mof_account_name": "Inventory write-down / impairment expense", "mof_account_name_mn": "Бараа материалын үнэ цэнийн бууралтын зардал", "parent_mof_account": "6000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "6800", "mof_account_name": "Impairment of assets", "mof_account_name_mn": "Хөрөнгийн үнэ цэнийн бууралтын зардал", "parent_mof_account": "6000", "is_group": 0, "root_type": "Expense"},
	
	# ============================================
	# 7xxx - FINANCE COSTS (САНХҮҮГИЙН ЗАРДАЛ)
	# ============================================
	{"mof_account_number": "7000", "mof_account_name": "Finance costs", "mof_account_name_mn": "Санхүүгийн зардал", "parent_mof_account": None, "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "7100", "mof_account_name": "Interest expense", "mof_account_name_mn": "Хүүгийн зардал", "parent_mof_account": "7000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "7200", "mof_account_name": "Foreign exchange loss", "mof_account_name_mn": "Валютын ханшийн зөрүүгийн алдагдал", "parent_mof_account": "7000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "7300", "mof_account_name": "Bank fees and commissions", "mof_account_name_mn": "Банкны шимтгэл, хураамж", "parent_mof_account": "7000", "is_group": 0, "root_type": "Expense"},
	
	# ============================================
	# 8xxx - OTHER NON-OPERATING EXPENSES (БУСАД ЗАРДАЛ)
	# ============================================
	{"mof_account_number": "8000", "mof_account_name": "Other non-operating expenses and losses", "mof_account_name_mn": "Бусад үйл ажиллагааны бус зардал ба гарз", "parent_mof_account": None, "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "8100", "mof_account_name": "Loss on disposal of PPE", "mof_account_name_mn": "Үндсэн хөрөнгө борлуулалтын алдагдал", "parent_mof_account": "8000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "8200", "mof_account_name": "Fines and penalties expense", "mof_account_name_mn": "Торгууль, алдангийн зардал", "parent_mof_account": "8000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "8300", "mof_account_name": "Charity and sponsorship", "mof_account_name_mn": "Буцалтгүй тусламж, ивээн тэтгэх зардал", "parent_mof_account": "8000", "is_group": 0, "root_type": "Expense"},
	
	# ============================================
	# 9xxx - TAX & OFF-BALANCE (ТАТВАР, ТЭНЦЛИЙН ГАДНАХ)
	# ============================================
	{"mof_account_number": "9000", "mof_account_name": "Income tax expense", "mof_account_name_mn": "Орлогын албан татварын зардал", "parent_mof_account": None, "is_group": 1, "root_type": "Expense"},
	{"mof_account_number": "9100", "mof_account_name": "Current income tax", "mof_account_name_mn": "Тухайн үеийн орлогын албан татвар", "parent_mof_account": "9000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "9200", "mof_account_name": "Deferred income tax", "mof_account_name_mn": "Хойшлогдсон орлогын албан татвар", "parent_mof_account": "9000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "9300", "mof_account_name": "Excise tax expense (non-creditable)", "mof_account_name_mn": "Хасагдах боломжгүй онцгой албан татварын зардал", "parent_mof_account": "9000", "is_group": 0, "root_type": "Expense"},
	{"mof_account_number": "9900", "mof_account_name": "Off-balance sheet accounts", "mof_account_name_mn": "Тэнцлийн гаднах данс", "parent_mof_account": None, "is_group": 1, "root_type": "Asset"},
	{"mof_account_number": "9910", "mof_account_name": "Leased assets off-balance", "mof_account_name_mn": "Түрээсийн үндсэн хөрөнгө (тэнцлийн гаднах)", "parent_mof_account": "9900", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "9920", "mof_account_name": "Guarantees given", "mof_account_name_mn": "Олгосон баталгаа, батлан даалт", "parent_mof_account": "9900", "is_group": 0, "root_type": "Asset"},
	{"mof_account_number": "9930", "mof_account_name": "Goods on consignment", "mof_account_name_mn": "Комиссийн журмаар хадгалж буй бараа", "parent_mof_account": "9900", "is_group": 0, "root_type": "Asset"},
]


def import_mof_accounts():
	"""
	Import all 154 MOF standard accounts into MOF Account Mapping.
	
	Called during eBalance app installation.
	"""
	imported = 0
	skipped = 0
	errors = []
	
	for account in MOF_ACCOUNTS:
		try:
			# Check if already exists
			if frappe.db.exists("MOF Account Mapping", account["mof_account_number"]):
				skipped += 1
				continue
			
			doc = frappe.new_doc("MOF Account Mapping")
			doc.mof_account_number = account["mof_account_number"]
			doc.mof_account_name = account["mof_account_name"]
			doc.mof_account_name_mn = account["mof_account_name_mn"]
			doc.parent_mof_account = account["parent_mof_account"]
			doc.is_group = account["is_group"]
			doc.root_type = account["root_type"]
			doc.enabled = 1
			doc.auto_mapped = 0
			
			doc.insert(ignore_permissions=True)
			imported += 1
			
		except Exception as e:
			errors.append(f"{account['mof_account_number']}: {str(e)}")
	
	frappe.db.commit()
	
	return {
		"imported": imported,
		"skipped": skipped,
		"errors": errors,
		"total": len(MOF_ACCOUNTS)
	}


@frappe.whitelist()
def setup_mof_accounts():
	"""
	Whitelisted method to import MOF accounts.
	Can be called from eBalance Settings page.
	"""
	result = import_mof_accounts()
	
	if result["errors"]:
		frappe.msgprint(
			_("Imported {0} MOF accounts. Skipped {1} existing. Errors: {2}").format(
				result["imported"], result["skipped"], len(result["errors"])
			),
			indicator="orange",
			title=_("Import Complete")
		)
	else:
		frappe.msgprint(
			_("Imported {0} of {1} MOF standard accounts. Skipped {2} existing.").format(
				result["imported"], result["total"], result["skipped"]
			),
			indicator="green",
			title=_("Import Successful")
		)
	
	return result


@frappe.whitelist()
def get_mof_account_stats():
	"""Get statistics about MOF account mappings"""
	total = frappe.db.count("MOF Account Mapping")
	mapped = frappe.db.sql("""
		SELECT COUNT(DISTINCT parent) 
		FROM `tabMOF Account Mapping Item`
	""")[0][0] or 0
	
	by_root_type = frappe.db.sql("""
		SELECT root_type, COUNT(*) as count
		FROM `tabMOF Account Mapping`
		GROUP BY root_type
	""", as_dict=True)
	
	groups = frappe.db.count("MOF Account Mapping", {"is_group": 1})
	leaves = frappe.db.count("MOF Account Mapping", {"is_group": 0})
	
	return {
		"total": total,
		"mapped": mapped,
		"groups": groups,
		"leaves": leaves,
		"by_root_type": by_root_type
	}
