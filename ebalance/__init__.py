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
- 154/154 MOF Standard Accounts (НББОУС) mapped
- Full ERPNext Trial Balance to MOF transformation
- Intelligent auto-mapping between ERPNext and MOF accounts
- Complete report generation workflow

Performance Optimizations (v1.1.1):
- Redis caching for MOF accounts and balances
- Connection pooling for API requests
- Batch database operations
- Precompiled keyword matching
- Optimized GL queries with indexes

Features (v1.2.0):
- Comprehensive logging utilities (logger.py)
- Autopilot mode for auto-fetch and auto-submit reports
- Incremental GL aggregation caching
- Multi-company entity support
"""

__version__ = "1.2.0"
