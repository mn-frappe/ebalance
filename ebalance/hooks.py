# -*- coding: utf-8 -*-
# Copyright (c) 2025, MN Frappe and contributors
# License: GNU General Public License v3

"""
eBalance - Mongolia Ministry of Finance Financial Reporting

Works with ERPNext and all ERPNext-based apps that create GL Entries:
- ERPNext Core: Chart of Accounts, GL Entry, Period Closing
- Healthcare: Patient billing GL entries
- Education: Student fees GL entries
- Lending: Loan accounting GL entries

eBalance reports aggregate data from ERPNext's General Ledger,
so it automatically includes transactions from all ERPNext-based apps.
"""

app_name = "ebalance"
app_title = "eBalance"
app_publisher = "Digital Consulting Service LLC (Mongolia)"
app_description = (
    "Mongolia Ministry of Finance eBalance Financial Reporting System. "
    "Works with ERPNext and all apps that create GL Entries (Healthcare, Education, Lending)."
)
app_email = "dev@frappe.mn"
app_license = "gpl-3.0"
app_logo_url = "/assets/ebalance/images/ebalance_logo.png"

# Required Apps - ERPNext required for Chart of Accounts and GL Entry
required_apps = ["frappe", "erpnext"]

# Includes in <head>
app_include_css = "/assets/ebalance/css/ebalance.css"
app_include_js = "/assets/ebalance/js/ebalance.js"

# Installation
after_install = "ebalance.setup.install.after_install"
after_migrate = "ebalance.setup.install.after_migrate"
before_uninstall = "ebalance.setup.install.before_uninstall"

# Error Reporting / Telemetry
# ---------------------------
# Reports unhandled exceptions to GitHub Issues (if enabled in settings)
exception_handler = "ebalance.ebalance.telemetry.on_error"

# Fixtures
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["module", "=", "eBalance"]]
    },
    {
        "doctype": "Property Setter",
        "filters": [["module", "=", "eBalance"]]
    },
    {
        "doctype": "Workspace",
        "filters": [["module", "=", "eBalance"]]
    },
    # Approval workflow fixtures (order matters: states before workflow)
    "ebalance/fixtures/ebalance_workflow_states.json",
    "ebalance/fixtures/ebalance_roles.json",
    "ebalance/fixtures/ebalance_workflow.json",
    "ebalance/fixtures/ebalance_notifications.json",
]

# DocType Events - ERPNext Integration
# eBalance works with GL Entry which is created by ALL ERPNext-based apps
# Healthcare, Education, Lending all create GL Entries that feed into eBalance reports
doc_events = {
    "Company": {
        "on_update": "ebalance.integrations.company.on_update",
    },
    "Period Closing Voucher": {
        "on_submit": "ebalance.integrations.period_closing.on_submit",
        "on_cancel": "ebalance.integrations.period_closing.on_cancel",
    },
    "GL Entry": {
        "on_update": "ebalance.integrations.gl_entry.on_update",
        "on_cancel": "ebalance.integrations.gl_entry.on_cancel",
    },
    # Account mapping for MOF standard chart
    "Account": {
        "on_update": "ebalance.integrations.account.on_update",
    },
}

# Scheduled Tasks
scheduler_events = {
    "hourly": [
        "ebalance.performance.auto_sync_report_periods",
    ],
    "daily": [
        "ebalance.tasks.daily.execute",
        "ebalance.performance.auto_submit_reports",
    ],
    "weekly": [
        "ebalance.tasks.weekly.execute",
        "ebalance.performance.ensure_indexes",
    ],
}

# Permissions
permission_query_conditions = {}
has_permission = {}

# Desk Notifications
notification_config = "ebalance.startup.boot.get_notification_config"

# Boot Session Info
boot_session = "ebalance.startup.boot.boot_session"

# Website Route Rules
website_route_rules = []

# Jinja Methods
jinja = {
    "methods": [
        "ebalance.utils.jinja.format_mnt",
        "ebalance.utils.jinja.format_ebalance_date",
        "ebalance.utils.jinja.get_period_status",
        "ebalance.utils.jinja.get_submission_status_badge",
        "ebalance.utils.jinja.get_ebalance_settings",
    ],
    "filters": [
        "ebalance.utils.jinja.ebalance_filters",
    ],
}

# Override standard methods
override_whitelisted_methods = {}

# Override doctype class
override_doctype_class = {}

# Standard Portal Menu Items
standard_portal_menu_items = []

# Workflow definitions
workflows = []

# User Data Protection
user_data_fields = []

# Authentication and Authorization
auth_hooks = []

# Testing
# before_tests = "ebalance.tests.setup.before_tests"
