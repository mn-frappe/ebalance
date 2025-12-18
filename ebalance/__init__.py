# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eBalance - Mongolia Financial Reporting System Integration for ERPNext

Integrates with Ministry of Finance (Сангийн яам) eBalance system for:
- Financial Statements (Санхүүгийн тайлан)
- Balance Sheet (Санхүү байдлын тайлан - СБТ)
- Income Statement (Орлогын үр дүнгийн тайлан - ОҮТ)
- Cash Flow Statement (Мөнгөн гүйлгээний тайлан - МГТ)

100% Integration Coverage:
- 10/10 eBalance API endpoints implemented
- 154/154 MOF Standard Accounts (НББОУС) mapped from mn_chart.csv
- Full ERPNext Trial Balance to MOF transformation
- Intelligent auto-mapping between ERPNext and MOF accounts
- Complete report generation workflow

100% MOF Chart of Accounts:
- All 154 accounts from mn_chart.csv imported as fixtures
- Account codes 1000-9900 with Mongolian names
- Full hierarchy: Assets, Liabilities, Equity, Revenue, Expenses

Performance Optimizations (v1.1.1):
- Redis caching for MOF accounts and balances
- Connection pooling for API requests
- Batch database operations
- Precompiled keyword matching
- Optimized GL queries with indexes

Features (v1.3.0):
- Comprehensive logging utilities (logger.py)
- Multi-level approval workflow for report submissions
- Incremental GL aggregation caching
- Multi-company entity support
- Complete MOF fixtures (mof_accounts.py)
"""

__version__ = "1.3.0"
