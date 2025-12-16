# -*- coding: utf-8 -*-
# Copyright (c) 2025, MN Frappe and contributors
# License: GNU General Public License v3

app_name = "ebalance"
app_title = "eBalance"
app_publisher = "MN Frappe"
app_description = "Mongolia Ministry of Finance eBalance Financial Reporting System Integration for ERPNext"
app_email = "info@1cloud.mn"
app_license = "gpl-3.0"
app_logo_url = "/assets/ebalance/images/ebalance_logo.png"

# Required Apps
required_apps = ["frappe"]

# Includes in <head>
app_include_css = "/assets/ebalance/css/ebalance.css"
app_include_js = "/assets/ebalance/js/ebalance.js"

# Installation
after_install = "ebalance.setup.install.after_install"
after_migrate = "ebalance.setup.install.after_migrate"
before_uninstall = "ebalance.setup.install.before_uninstall"

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
    }
]

# DocType Events - ERPNext Integration
doc_events = {}

def _setup_doc_events():
    """Dynamically setup doc_events based on installed apps"""
    global doc_events
    import frappe
    
    # Base events (always available)
    base_events = {}
    
    # ERPNext specific events
    erpnext_events = {
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
    }
    
    # Check if ERPNext is installed
    try:
        if "erpnext" in frappe.get_installed_apps():
            doc_events.update(erpnext_events)
    except Exception:
        pass
    
    doc_events.update(base_events)

# Initialize doc_events at module load
try:
    _setup_doc_events()
except Exception:
    pass

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "ebalance.tasks.daily.execute",
    ],
    "weekly": [
        "ebalance.tasks.weekly.execute",
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
