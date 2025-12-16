# eBalance v1.1.0

<div align="center">

**Mongolia Ministry of Finance (Сангийн яам) eBalance Financial Reporting System Integration for ERPNext**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Frappe](https://img.shields.io/badge/Frappe-v15-blue)](https://frappeframework.com)
[![ERPNext](https://img.shields.io/badge/ERPNext-v15-blue)](https://erpnext.com)

</div>

---

## 🌟 Overview

eBalance is a comprehensive Frappe/ERPNext application that integrates with Mongolia's Ministry of Finance electronic balance reporting system (Цахим санхүүгийн тайлангийн систем). It enables businesses to generate and submit financial reports directly from ERPNext to the MOF eBalance portal.

### Key Features

- **100% API Coverage**: All 10 eBalance API endpoints implemented
- **154 MOF Standard Accounts**: Complete НББОУС (Mongolian Standard Chart of Accounts) mapping
- **Intelligent Auto-Mapping**: Automatically maps ERPNext accounts to MOF codes
- **Bilingual Reports**: Mongolian and English report generation
- **One-Click Submission**: Generate → Save Draft → Submit workflow
- **Audit Trail**: Complete logging of all API interactions

---

## 📊 How It Works

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ERPNext                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  GL Entry    │  │   Account    │  │    Company               │   │
│  │  (Journal)   │  │ (Chart)      │  │    (Settings)            │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │
│         │                 │                        │                 │
│         └────────────────►│◄───────────────────────┘                 │
│                           │                                          │
│  ┌────────────────────────▼─────────────────────────────────────┐   │
│  │                    eBalance App                               │   │
│  │  ┌─────────────────────────────────────────────────────────┐ │   │
│  │  │  MOF Account Mapping (154 accounts)                      │ │   │
│  │  │  ┌─────────┐    ┌─────────┐    ┌─────────┐             │ │   │
│  │  │  │ 1xxx    │    │ 2xxx    │    │ 3-9xxx  │             │ │   │
│  │  │  │ Assets  │    │ Liabili │    │ Others  │             │ │   │
│  │  │  └────┬────┘    └────┬────┘    └────┬────┘             │ │   │
│  │  └───────┼──────────────┼──────────────┼────────────────────┘ │   │
│  │          │              │              │                      │   │
│  │  ┌───────▼──────────────▼──────────────▼────────────────────┐ │   │
│  │  │              Report Transformer                           │ │   │
│  │  │    GL Entries → Trial Balance → MOF Format               │ │   │
│  │  └─────────────────────────┬────────────────────────────────┘ │   │
│  │                            │                                   │   │
│  │  ┌─────────────────────────▼────────────────────────────────┐ │   │
│  │  │              eBalance API Client                          │ │   │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │   │
│  │  │  │ Auth     │ │ Periods  │ │ Reports  │ │ Submit   │   │ │   │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │   │
│  │  └─────────────────────────┬────────────────────────────────┘ │   │
│  └────────────────────────────┼──────────────────────────────────┘   │
└───────────────────────────────┼──────────────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   ITC OAuth2 Server    │
                    │  auth.itc.gov.mn       │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   MOF eBalance API     │
                    │  inspector-ebalance    │
                    │     .mof.gov.mn        │
                    └───────────────────────┘
```

### Workflow

```
1. SETUP
   ┌─────────────────────────────────────────────────────┐
   │  eBalance Settings                                   │
   │  - Configure credentials (ITC SSO)                  │
   │  - Select environment (Staging/Production)          │
   │  - Test connection                                   │
   │  - Import 154 MOF accounts                          │
   │  - Auto-map ERPNext accounts to MOF codes           │
   └─────────────────────────────────────────────────────┘
                          ▼
2. MAP ACCOUNTS
   ┌─────────────────────────────────────────────────────┐
   │  MOF Account Mapping                                 │
   │  - Link ERPNext accounts to MOF codes               │
   │  - Automatic matching by number/name                │
   │  - Manual mapping for special cases                 │
   │                                                      │
   │  ERPNext Account          →  MOF Code               │
   │  "1111 - Cash MNT"        →  1112 (Bank MNT)       │
   │  "2100 - Trade Payables"  →  2110 (Trade payables) │
   └─────────────────────────────────────────────────────┘
                          ▼
3. GENERATE REPORT
   ┌─────────────────────────────────────────────────────┐
   │  eBalance Report Request                             │
   │  - Select company and fiscal year                   │
   │  - Click "Generate Report Data"                     │
   │  - Preview Balance Sheet (СБТ) / Income Stmt (ОҮТ) │
   │  - Validate A = L + E balance check                 │
   └─────────────────────────────────────────────────────┘
                          ▼
4. SUBMIT TO MOF
   ┌─────────────────────────────────────────────────────┐
   │  Submission Flow                                     │
   │  - "Save to eBalance" → Draft saved at MOF          │
   │  - "Submit Report" → Final submission               │
   │  - "Check Status" → Poll for confirmation           │
   │  - Status: Draft → In Progress → Submitted → Done   │
   └─────────────────────────────────────────────────────┘
```

---

## 📁 Module Structure

```
ebalance/
├── api/                          # API Layer
│   ├── auth.py                   # ITC OAuth2 authentication
│   ├── client.py                 # eBalance API client (10 endpoints)
│   ├── http_client.py            # HTTP request handler
│   ├── transformer.py            # GL → MOF data transformation
│   └── auto_mapping.py           # Intelligent account mapping
│
├── ebalance/                     # Frappe Module
│   ├── doctype/
│   │   ├── ebalance_settings/    # Configuration (singleton)
│   │   ├── ebalance_report_period/   # Synced periods from MOF
│   │   ├── ebalance_report_request/  # Report submissions
│   │   ├── ebalance_submission_log/  # Audit trail
│   │   ├── mof_account_mapping/      # ERPNext ↔ MOF mapping
│   │   └── mof_report_form_row/      # Form row definitions
│   │
│   └── report/
│       ├── mof_balance_sheet/    # СБТ - Balance Sheet Report
│       └── mof_income_statement/ # ОҮТ - Income Statement Report
│
├── fixtures/
│   └── mof_accounts.py           # 154 НББОУС standard accounts
│
├── integrations/                 # ERPNext Integration
│   ├── company.py               # Company hooks
│   ├── gl_entry.py              # GL Entry processing
│   ├── period_closing.py        # Period closing triggers
│   └── trial_balance.py         # Trial balance extraction
│
├── setup/
│   └── install.py               # Post-install setup
│
└── tasks/
    ├── daily.py                 # Daily scheduled tasks
    └── weekly.py                # Weekly scheduled tasks
```

---

## 📋 MOF Standard Accounts (НББОУС)

154 accounts covering all categories:

| Range | Category (EN) | Category (MN) | Count |
|-------|---------------|---------------|-------|
| 1000-1990 | Assets | Хөрөнгө | 55 |
| 2000-2490 | Liabilities | Өр төлбөр | 29 |
| 3000-3600 | Equity | Өмч | 12 |
| 4000-4400 | Revenue | Орлого | 15 |
| 5000-5130 | Cost of Sales | Борлуулалтын өртөг | 5 |
| 6000-6800 | Operating Expenses | Үйл ажиллагааны зардал | 22 |
| 7000-7300 | Finance Costs | Санхүүгийн зардал | 4 |
| 8000-8300 | Other Expenses | Бусад зардал | 4 |
| 9000-9930 | Tax & Off-balance | Татвар, тэнцлийн гаднах | 8 |

---

## 📈 Reports

### MOF Balance Sheet (СБТ - Санхүү байдлын тайлан)

Generates balance sheet in MOF format with:
- **Assets Section**: Current assets, Non-current assets
- **Liabilities Section**: Current liabilities, Non-current liabilities  
- **Equity Section**: Share capital, Retained earnings, Reserves
- **Balance Check**: Validates A = L + E

### MOF Income Statement (ОҮТ - Орлогын үр дүнгийн тайлан)

Generates income statement with:
- **Revenue**: Sales, Services, Other income
- **Cost of Sales**: COGS, Cost of services
- **Operating Expenses**: Selling, Admin, Depreciation
- **Finance Income/Costs**: Interest, Exchange gains/losses
- **Tax Expense**: Current and deferred tax
- **Net Profit**: Bottom line calculation

---

## ⚙️ Installation

### Requirements

- Frappe Framework v15+
- ERPNext v15+ (optional, for full GL integration)
- Python 3.10+
- Valid MOF eBalance credentials

### Install via bench

```bash
# Get the app
bench get-app https://github.com/mn-frappe/ebalance.git

# Install on your site
bench --site [sitename] install-app ebalance

# Run migrations
bench --site [sitename] migrate
```

### Post-Installation

The app automatically:
1. Creates MN Settings workspace (if not exists)
2. Imports 154 MOF standard accounts
3. Sets up default configuration

---

## 🔧 Configuration

### Step 1: eBalance Settings

Navigate to **MN Settings > eBalance > eBalance Settings**

| Field | Description |
|-------|-------------|
| Environment | Staging (test) or Production (live) |
| Username | ITC SSO username (ЧЕ-xxxxxxxx) |
| Password | ITC SSO password |
| Organization Reg No | Company registration number |

### Step 2: Test Connection

1. Click **Test Connection** button
2. Verify "✅ Connected" status
3. Click **Sync Periods** to fetch available report periods

### Step 3: Import MOF Accounts

1. Go to **MOF Accounts** button group
2. Click **Import MOF Accounts** (imports 154 standard accounts)
3. Click **Auto-Map ERPNext Accounts** (intelligent mapping)

### Step 4: Review Mappings

1. Open **MOF Account Mapping** list
2. Review auto-mapped accounts
3. Manually map any unmapped accounts

---

## 📝 Usage Guide

### Creating a Financial Report

1. **Create Report Request**
   - Go to eBalance > eBalance Report Request > New
   - Select Company
   - Select Fiscal Year or Date Range
   - Choose Report Type (Balance Sheet, Income Statement, or Combined)

2. **Generate Data**
   - Click **Generate Report Data**
   - Preview appears in Balance Sheet / Income Statement fields
   - Review and verify totals

3. **Submit to MOF**
   - Click **Save to eBalance** (creates draft at MOF)
   - Status changes to "In Progress"
   - Click **Submit Report** (final submission)
   - Click **Check Status** to poll for confirmation

### Viewing Reports

- **MOF Balance Sheet**: Query Report > MOF Balance Sheet
- **MOF Income Statement**: Query Report > MOF Income Statement

---

## 🔌 API Endpoints

eBalance implements all 10 MOF API endpoints:

| # | Endpoint | Method | Description |
|---|----------|--------|-------------|
| 1 | `getWritingConfigs` | GET | Get available report periods (тайлант үе) |
| 2 | `getUserRoles` | GET | Get user permissions for organization |
| 3 | `getAllConfigWithReportOrgList` | GET | Get connected periods for company |
| 4 | `getReportUserOrgHdrList` | GET | Get existing report requests |
| 5 | `decideReportUserOrgHdr` | GET | Initialize report entry session |
| 6 | `getReportData` | GET | Get form structure and cell IDs |
| 7 | `getReportPackageMap` | GET | Get available form types |
| 8 | `saveReportData` | POST | Save draft report to MOF |
| 9 | `sendReportData` | POST | Submit final report |
| 10 | `getConfirmedReportData` | GET | Query confirmed reports |

---

## 🌐 Server URLs

| Environment | API URL | Auth URL |
|-------------|---------|----------|
| Staging | https://st-inspector-ebalance.mof.gov.mn | https://st.auth.itc.gov.mn |
| Production | https://inspector-ebalance.mof.gov.mn | https://auth.itc.gov.mn |

---

## 📋 DocTypes

| DocType | Type | Description |
|---------|------|-------------|
| eBalance Settings | Single | Configuration (credentials, environment) |
| eBalance Report Period | List | Synced periods from MOF |
| eBalance Report Request | List | Report submissions |
| eBalance Submission Log | List | Audit trail |
| MOF Account Mapping | List | ERPNext ↔ MOF account mapping |
| MOF Report Form Row | Child | Form row definitions |

---

## 🔒 Security

- **Encrypted Storage**: Passwords stored using Frappe's encrypted Password fieldtype
- **OAuth2 Tokens**: Cached with automatic refresh before expiry
- **HTTPS Only**: All API communications encrypted
- **Audit Trail**: Complete logging in eBalance Submission Log
- **Role-Based Access**: Accounts Manager, Accounts User roles required

---

## 🧪 Testing

```bash
# Run all tests
bench --site [sitename] run-tests --app ebalance

# Run specific test
bench --site [sitename] run-tests --module ebalance.tests.test_ebalance
```

---

## 📚 Related Apps

eBalance integrates with the MN Settings workspace alongside:

| App | Description | Integration |
|-----|-------------|-------------|
| **QPay** | QPay payment gateway | Payment collection |
| **eBarimt** | VAT invoice system | Tax invoicing |
| **eBalance** | Financial reporting | MOF submission |

---

## 🤝 Contributing

```bash
cd apps/ebalance
pre-commit install
```

Tools: ruff, eslint, prettier, pyupgrade

---

## 📄 License

GNU General Public License v3.0

---

## 📞 Support

- **GitHub Issues**: https://github.com/mn-frappe/ebalance/issues
- **Email**: info@1cloud.mn

---

## 👥 Credits

Developed by **MN Frappe** for the Mongolian ERPNext community.

---

<div align="center">

**eBalance v1.1.0** | 100% MOF Integration | 154 Standard Accounts

</div>
