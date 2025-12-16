# eBalance v1.0.0

Mongolia Ministry of Finance (Сангийн яам) eBalance Financial Reporting System Integration for ERPNext.

## Overview

eBalance is a Frappe/ERPNext application that integrates with Mongolia's Ministry of Finance electronic balance reporting system. It enables businesses to submit financial reports (Trial Balance, Balance Sheet, Profit & Loss) directly from ERPNext to the MOF eBalance portal.

## Features

- **3-Tab Settings Interface**: Connection | Automation | Advanced
- **ITC OAuth2 Authentication**: Secure integration with auth.itc.gov.mn
- **Automatic Period Sync**: Sync available reporting periods from MOF
- **Trial Balance Integration**: Extract data from ERPNext Chart of Accounts
- **Report Submission**: Submit financial reports directly to MOF
- **Audit Trail**: Complete logging of all API interactions
- **ERPNext Integration**: Works seamlessly with Company, GL Entry, Period Closing Voucher
- **MN Settings Workspace**: Integrates with QPay, eBarimt when installed together

## Installation

### Requirements

- Frappe Framework v15+
- ERPNext v15+ (optional, for full integration)
- Python 3.10+

### Install via bench

```bash
# Get the app
bench get-app https://github.com/mn-frappe/ebalance.git

# Install on your site
bench --site [sitename] install-app ebalance

# Run migrations
bench --site [sitename] migrate
```

## Configuration

1. Navigate to **MN Settings > eBalance > eBalance Settings**
2. Enter your MOF credentials:
   - Username (ЧЕ-xxxxxxxx)
   - Password
   - Organization Registration Number
3. Select Environment (Staging/Production)
4. Click **Test Connection** to verify
5. Enable the integration

## API Endpoints

eBalance integrates with the following MOF API endpoints:

| Endpoint | Description |
|----------|-------------|
| `getWritingConfigs` | Get available report periods |
| `getUserRoles` | Get user permissions |
| `getAllConfigWithReportOrgList` | Get connected periods |
| `getReportUserOrgHdrList` | Get report requests |
| `decideReportUserOrgHdr` | Start report entry |
| `getReportData` | Get form + validation rules |
| `getReportPackageMap` | Get form names |
| `saveReportData` | Save draft report |
| `sendReportData` | Submit final report |
| `getConfirmedReportData` | Query confirmed reports |

## Server URLs

| Environment | URL |
|-------------|-----|
| Staging | https://st-inspector-ebalance.mof.gov.mn |
| Production | https://inspector-ebalance.mof.gov.mn |
| Auth | https://auth.itc.gov.mn/auth/realms/ITC |

## DocTypes

- **eBalance Settings**: Configuration (single)
- **eBalance Report Period**: Synced periods from MOF
- **eBalance Report Request**: Report submissions
- **eBalance Submission Log**: Audit trail

## Workspaces

- **MN Settings**: Parent workspace for Mongolian integrations (QPay, eBarimt, eBalance)
- **eBalance**: Main workspace with shortcuts and links

## Security

- Passwords stored using Frappe's encrypted Password fieldtype
- OAuth2 tokens cached with automatic refresh
- All API communications over HTTPS
- Comprehensive error logging (excluding sensitive data)

## Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/ebalance
pre-commit install
```

Tools used: ruff, eslint, prettier, pyupgrade

## License

GNU General Public License v3.0

## Support

- **GitHub Issues**: https://github.com/mn-frappe/ebalance/issues
- **Email**: info@1cloud.mn

## Credits

Developed by MN Frappe for the Mongolian ERPNext community.

---

**Note**: This app requires valid credentials from the Ministry of Finance to function.

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

gpl-3.0
