// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.query_reports["VAT Reconciliation"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        if (data && data.bold) {
            value = "<b>" + value + "</b>";
        }
        
        if (column.fieldname === "status") {
            if (value && value.includes("Reconciled")) {
                value = "<span class='text-success'>" + value + "</span>";
            } else if (value && value.includes("Discrepancy")) {
                value = "<span class='text-danger'>" + value + "</span>";
            }
        }
        
        if (column.fieldname === "difference" && data && data.difference) {
            if (data.difference > 0) {
                value = "<span class='text-danger'>" + value + "</span>";
            } else if (data.difference < 0) {
                value = "<span class='text-warning'>" + value + "</span>";
            }
        }
        
        return value;
    },
    
    "onload": function(report) {
        // Add quick date range buttons
        report.page.add_inner_button(__("This Month"), function() {
            const today = frappe.datetime.get_today();
            const first_day = frappe.datetime.month_start();
            report.set_filter_value("from_date", first_day);
            report.set_filter_value("to_date", today);
            report.refresh();
        });
        
        report.page.add_inner_button(__("Last Month"), function() {
            const today = new Date();
            const first_day = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            const last_day = new Date(today.getFullYear(), today.getMonth(), 0);
            report.set_filter_value("from_date", frappe.datetime.obj_to_str(first_day));
            report.set_filter_value("to_date", frappe.datetime.obj_to_str(last_day));
            report.refresh();
        });
        
        report.page.add_inner_button(__("This Quarter"), function() {
            const today = new Date();
            const quarter = Math.floor(today.getMonth() / 3);
            const first_day = new Date(today.getFullYear(), quarter * 3, 1);
            report.set_filter_value("from_date", frappe.datetime.obj_to_str(first_day));
            report.set_filter_value("to_date", frappe.datetime.get_today());
            report.refresh();
        });
    }
};
