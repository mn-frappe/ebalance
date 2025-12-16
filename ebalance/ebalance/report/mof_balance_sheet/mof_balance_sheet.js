// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.query_reports["MOF Balance Sheet"] = {
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
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			"on_change": function() {
				var fiscal_year = frappe.query_report.get_filter_value('fiscal_year');
				if (fiscal_year) {
					frappe.call({
						method: "erpnext.accounts.utils.get_fiscal_year",
						args: {
							fiscal_year: fiscal_year
						},
						callback: function(r) {
							if (r.message) {
								frappe.query_report.set_filter_value({
									from_date: r.message[1],
									to_date: r.message[2]
								});
							}
						}
					});
				}
			}
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -12),
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
		
		// Bold total rows
		if (data && data.is_total) {
			value = "<b>" + value + "</b>";
		}
		
		// Highlight balance check error
		if (data && data.row_code === "" && data.balance !== 0) {
			value = "<span style='color: red'>" + value + "</span>";
		}
		
		return value;
	},
	"tree": true,
	"name_field": "account_name_mn",
	"parent_field": "",
	"initial_depth": 2
};
