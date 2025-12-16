// Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
// License: GNU General Public License v3

frappe.ui.form.on("eBalance Report Request", {
	refresh: function(frm) {
		// Add custom buttons based on status
		frm.add_custom_button(__("MOF Balance Sheet"), function() {
			frappe.set_route("query-report", "MOF Balance Sheet", {
				company: frm.doc.company,
				from_date: frm.doc.from_date,
				to_date: frm.doc.to_date
			});
		}, __("Reports"));
		
		frm.add_custom_button(__("MOF Income Statement"), function() {
			frappe.set_route("query-report", "MOF Income Statement", {
				company: frm.doc.company,
				from_date: frm.doc.from_date,
				to_date: frm.doc.to_date
			});
		}, __("Reports"));
		
		// Status-based buttons
		if (frm.doc.docstatus === 0) {
			// Draft document
			if (frm.doc.status === "Draft" || !frm.doc.status) {
				frm.add_custom_button(__("Generate Report Data"), function() {
					frm.call({
						method: "generate_report_data",
						doc: frm.doc,
						freeze: true,
						freeze_message: __("Generating MOF report data from GL Entries..."),
						callback: function(r) {
							if (r.message) {
								frm.reload_doc();
								frappe.show_alert({
									message: __("Report data generated successfully"),
									indicator: "green"
								});
							}
						}
					});
				}).addClass("btn-primary");
			}
			
			if (frm.doc.status === "Ready") {
				frm.add_custom_button(__("Save to eBalance"), function() {
					frappe.confirm(
						__("Save this report as draft to Ministry of Finance eBalance system?"),
						function() {
							frm.call({
								method: "save_to_ebalance",
								doc: frm.doc,
								freeze: true,
								freeze_message: __("Saving to MOF eBalance..."),
								callback: function(r) {
									frm.reload_doc();
									if (r.message && r.message.success) {
										frappe.show_alert({
											message: __("Saved to eBalance successfully"),
											indicator: "green"
										});
									}
								}
							});
						}
					);
				}).addClass("btn-primary");
			}
			
			if (frm.doc.status === "In Progress") {
				frm.add_custom_button(__("Submit Report"), function() {
					frappe.confirm(
						__("Submit this report to Ministry of Finance for final review? This action cannot be undone."),
						function() {
							frm.call({
								method: "submit_report",
								doc: frm.doc,
								freeze: true,
								freeze_message: __("Submitting to MOF..."),
								callback: function(r) {
									frm.reload_doc();
									if (r.message && r.message.success) {
										frappe.show_alert({
											message: __("Report submitted successfully"),
											indicator: "green"
										});
									}
								}
							});
						}
					);
				}).addClass("btn-danger");
				
				frm.add_custom_button(__("Check Status"), function() {
					frm.call({
						method: "check_status",
						doc: frm.doc,
						freeze: true,
						freeze_message: __("Checking status..."),
						callback: function(r) {
							frm.reload_doc();
						}
					});
				});
			}
		}
		
		// Show validation errors if any
		if (frm.doc.validation_errors) {
			frm.dashboard.clear_headline();
			frm.dashboard.set_headline_alert(
				__("Validation Errors: ") + frm.doc.validation_errors,
				"red"
			);
		}
		
		// Show status indicator
		if (frm.doc.status) {
			let indicator = get_status_indicator(frm.doc.status);
			frm.page.set_indicator(frm.doc.status, indicator);
		}
	},
	
	company: function(frm) {
		// Clear data when company changes
		frm.set_value("balance_sheet_preview", "");
		frm.set_value("income_statement_preview", "");
		frm.set_value("report_summary", "");
	},
	
	fiscal_year: function(frm) {
		if (frm.doc.fiscal_year) {
			frappe.call({
				method: "erpnext.accounts.utils.get_fiscal_year",
				args: {
					fiscal_year: frm.doc.fiscal_year
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value("from_date", r.message[1]);
						frm.set_value("to_date", r.message[2]);
					}
				}
			});
		}
	},
	
	report_type: function(frm) {
		// Update form based on report type
		update_form_visibility(frm);
	}
});

function get_status_indicator(status) {
	const indicators = {
		"Draft": "orange",
		"Generating": "blue",
		"Ready": "green",
		"In Progress": "yellow",
		"Submitted": "blue",
		"Confirmed": "green",
		"Rejected": "red",
		"Failed": "red"
	};
	return indicators[status] || "gray";
}

function update_form_visibility(frm) {
	// Show/hide fields based on report type
	let is_balance = frm.doc.report_type === "Balance Sheet";
	let is_income = frm.doc.report_type === "Income Statement";
	
	frm.toggle_display("balance_sheet_preview", is_balance || frm.doc.report_type === "Combined");
	frm.toggle_display("income_statement_preview", is_income || frm.doc.report_type === "Combined");
}
