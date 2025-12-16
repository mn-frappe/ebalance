/**
 * eBalance App JavaScript
 * Copyright (c) 2025, MN Frappe
 */

// eBalance namespace
frappe.provide("ebalance");

/**
 * Initialize eBalance module
 */
ebalance.init = function() {
    // Check if eBalance is enabled
    if (frappe.boot.ebalance && frappe.boot.ebalance.enabled) {
        ebalance.setup_notifications();
        ebalance.setup_shortcuts();
    }
};

/**
 * Setup notifications for upcoming deadlines
 */
ebalance.setup_notifications = function() {
    if (!frappe.boot.ebalance) return;
    
    const deadlines = frappe.boot.ebalance.upcoming_deadlines || [];
    
    if (deadlines.length > 0) {
        // Show notification for urgent deadlines (within 3 days)
        const urgent = deadlines.filter(d => {
            const deadline = frappe.datetime.str_to_obj(d.deadline);
            const now = new Date();
            const diff = (deadline - now) / (1000 * 60 * 60 * 24);
            return diff <= 3;
        });
        
        if (urgent.length > 0) {
            frappe.show_alert({
                message: __("{0} eBalance report(s) due within 3 days", [urgent.length]),
                indicator: "orange"
            }, 10);
        }
    }
};

/**
 * Setup keyboard shortcuts
 */
ebalance.setup_shortcuts = function() {
    // Alt+B to open eBalance Settings
    frappe.ui.keys.add_shortcut({
        shortcut: "alt+b",
        action: () => frappe.set_route("Form", "eBalance Settings"),
        page: "*",
        description: __("Open eBalance Settings"),
        ignore_inputs: true
    });
};

/**
 * Test API connection
 * @param {Function} callback - Callback function
 */
ebalance.test_connection = function(callback) {
    frappe.call({
        method: "ebalance.ebalance.doctype.ebalance_settings.ebalance_settings.test_connection",
        freeze: true,
        freeze_message: __("Testing connection to MOF..."),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __("Connection successful!"),
                    indicator: "green"
                });
            } else {
                frappe.show_alert({
                    message: __("Connection failed: {0}", [r.message?.error || "Unknown error"]),
                    indicator: "red"
                });
            }
            
            if (callback) callback(r.message);
        }
    });
};

/**
 * Sync report periods from MOF
 * @param {Function} callback - Callback function
 */
ebalance.sync_periods = function(callback) {
    frappe.call({
        method: "ebalance.ebalance.doctype.ebalance_settings.ebalance_settings.sync_periods",
        freeze: true,
        freeze_message: __("Syncing report periods..."),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __("Synced {0} period(s)", [r.message.synced_count || 0]),
                    indicator: "green"
                });
            } else {
                frappe.show_alert({
                    message: __("Sync failed: {0}", [r.message?.error || "Unknown error"]),
                    indicator: "red"
                });
            }
            
            if (callback) callback(r.message);
        }
    });
};

/**
 * Preview report data before submission
 * @param {string} company - Company name
 * @param {string} from_date - Period start date
 * @param {string} to_date - Period end date
 * @param {string} report_type - Type of report
 * @param {Function} callback - Callback function
 */
ebalance.preview_report = function(company, from_date, to_date, report_type, callback) {
    frappe.call({
        method: "ebalance.integrations.trial_balance.preview_ebalance_data",
        args: {
            company: company,
            from_date: from_date,
            to_date: to_date,
            report_type: report_type || "trial_balance"
        },
        freeze: true,
        freeze_message: __("Loading report preview..."),
        callback: function(r) {
            if (callback) callback(r.message);
        }
    });
};

/**
 * Submit report to MOF
 * @param {string} report_request - Report Request name
 * @param {Function} callback - Callback function
 */
ebalance.submit_report = function(report_request, callback) {
    frappe.confirm(
        __("Are you sure you want to submit this report to MOF? This action cannot be undone."),
        function() {
            frappe.call({
                method: "ebalance.ebalance.doctype.ebalance_report_request.ebalance_report_request.submit_to_mof",
                args: {
                    report_request: report_request
                },
                freeze: true,
                freeze_message: __("Submitting report to MOF..."),
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __("Report submitted successfully!"),
                            indicator: "green"
                        });
                        frappe.set_route("Form", "eBalance Report Request", report_request);
                    } else {
                        frappe.msgprint({
                            title: __("Submission Failed"),
                            message: r.message?.error || __("Unknown error occurred"),
                            indicator: "red"
                        });
                    }
                    
                    if (callback) callback(r.message);
                }
            });
        }
    );
};

/**
 * Format amount in MNT currency
 * @param {number} amount - Amount to format
 * @returns {string} - Formatted amount
 */
ebalance.format_mnt = function(amount) {
    if (amount === null || amount === undefined) return "₮0.00";
    
    return new Intl.NumberFormat("mn-MN", {
        style: "currency",
        currency: "MNT",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
};

/**
 * Get status indicator color
 * @param {string} status - Status value
 * @returns {string} - Indicator color
 */
ebalance.get_status_color = function(status) {
    const colors = {
        "Draft": "grey",
        "In Progress": "yellow",
        "Pending": "orange",
        "Submitted": "green",
        "Confirmed": "blue",
        "Error": "red",
        "Rejected": "red",
        "Active": "green",
        "Closed": "blue",
        "Expired": "red"
    };
    
    return colors[status] || "grey";
};

/**
 * Show report preview dialog
 * @param {Object} data - Preview data
 */
ebalance.show_preview_dialog = function(data) {
    if (!data || !data.accounts) {
        frappe.msgprint(__("No data available for preview"));
        return;
    }
    
    let table_html = `
        <table class="ebalance-preview-table">
            <thead>
                <tr>
                    <th>${__("Account")}</th>
                    <th class="number">${__("Opening Debit")}</th>
                    <th class="number">${__("Opening Credit")}</th>
                    <th class="number">${__("Debit")}</th>
                    <th class="number">${__("Credit")}</th>
                    <th class="number">${__("Closing Debit")}</th>
                    <th class="number">${__("Closing Credit")}</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    data.accounts.forEach(acc => {
        table_html += `
            <tr>
                <td>${acc.account || ""}</td>
                <td class="number">${ebalance.format_mnt(acc.opening_debit)}</td>
                <td class="number">${ebalance.format_mnt(acc.opening_credit)}</td>
                <td class="number">${ebalance.format_mnt(acc.debit)}</td>
                <td class="number">${ebalance.format_mnt(acc.credit)}</td>
                <td class="number">${ebalance.format_mnt(acc.closing_debit)}</td>
                <td class="number">${ebalance.format_mnt(acc.closing_credit)}</td>
            </tr>
        `;
    });
    
    // Totals row
    const totals = data.totals || {};
    table_html += `
            <tr class="total-row">
                <td><strong>${__("Total")}</strong></td>
                <td class="number">${ebalance.format_mnt(totals.opening_debit)}</td>
                <td class="number">${ebalance.format_mnt(totals.opening_credit)}</td>
                <td class="number">${ebalance.format_mnt(totals.debit)}</td>
                <td class="number">${ebalance.format_mnt(totals.credit)}</td>
                <td class="number">${ebalance.format_mnt(totals.closing_debit)}</td>
                <td class="number">${ebalance.format_mnt(totals.closing_credit)}</td>
            </tr>
        </tbody>
    </table>
    `;
    
    let d = new frappe.ui.Dialog({
        title: __("Report Preview"),
        size: "extra-large",
        fields: [
            {
                fieldtype: "HTML",
                options: `<div class="ebalance-preview-container">${table_html}</div>`
            }
        ],
        primary_action_label: __("Close"),
        primary_action: function() {
            d.hide();
        }
    });
    
    d.show();
};

// Initialize on ready
$(document).ready(function() {
    ebalance.init();
});
