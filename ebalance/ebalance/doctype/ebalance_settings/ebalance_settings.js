frappe.ui.form.on('eBalance Settings', {
	refresh: function(frm) {
		// Add custom buttons
		frm.add_custom_button(__('Test Connection'), function() {
			frm.call('test_connection').then(r => {
				if (r.message && r.message.success) {
					frappe.show_alert({
						message: __('Connection successful!'),
						indicator: 'green'
					});
				}
				frm.reload_doc();
			});
		}, __('Actions'));
		
		frm.add_custom_button(__('Sync Periods'), function() {
			frm.call('sync_report_periods').then(r => {
				if (r.message) {
					frappe.show_alert({
						message: __('Synced {0} periods', [r.message.total]),
						indicator: 'green'
					});
				}
				frm.reload_doc();
			});
		}, __('Actions'));
		
		// MOF Account Management buttons
		frm.add_custom_button(__('Import MOF Accounts'), function() {
			frappe.call({
				method: 'ebalance.fixtures.mof_accounts.setup_mof_accounts',
				freeze: true,
				freeze_message: __('Importing 154 MOF Standard Accounts...'),
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: __('Imported {0} accounts, skipped {1} existing', 
								[r.message.imported, r.message.skipped]),
							indicator: 'green'
						});
					}
				}
			});
		}, __('MOF Accounts'));
		
		frm.add_custom_button(__('Auto-Map ERPNext Accounts'), function() {
			frappe.confirm(
				__('Auto-map ERPNext accounts to MOF codes based on account numbers and names?'),
				function() {
					frappe.call({
						method: 'ebalance.api.auto_mapping.run_auto_mapping',
						args: {
							dry_run: false
						},
						freeze: true,
						freeze_message: __('Auto-mapping accounts...'),
						callback: function(r) {
							if (r.message) {
								frappe.msgprint({
									title: __('Auto-Mapping Results'),
									message: __('Matched: {0}<br>Need Manual Review: {1}',
										[r.message.matched.length, r.message.unmatched.length]),
									indicator: 'green'
								});
							}
						}
					});
				}
			);
		}, __('MOF Accounts'));
		
		frm.add_custom_button(__('Preview Auto-Map'), function() {
			frappe.call({
				method: 'ebalance.api.auto_mapping.run_auto_mapping',
				args: {
					dry_run: true
				},
				freeze: true,
				freeze_message: __('Analyzing accounts...'),
				callback: function(r) {
					if (r.message) {
						show_mapping_preview(r.message);
					}
				}
			});
		}, __('MOF Accounts'));
		
		// Show connection status indicator
		if (frm.doc.connection_status) {
			if (frm.doc.connection_status.includes('✅')) {
				frm.dashboard.set_headline_alert(
					'<span class="indicator green">Connected to eBalance</span>'
				);
			} else if (frm.doc.connection_status.includes('❌')) {
				frm.dashboard.set_headline_alert(
					'<span class="indicator red">Not connected - check credentials</span>'
				);
			}
		}
		
		// Environment change warning
		if (frm.doc.environment === 'Production') {
			frm.dashboard.add_comment(
				__('You are connected to the PRODUCTION eBalance server. All submissions are real.'),
				'yellow',
				true
			);
		}
	},
	
	environment: function(frm) {
		// Update URLs when environment changes
		const auth_urls = {
			'Staging': 'https://st.auth.itc.gov.mn/auth/realms/Staging',
			'Production': 'https://auth.itc.gov.mn/auth/realms/ITC'
		};
		const api_urls = {
			'Staging': 'https://st-inspector-ebalance.mof.gov.mn',
			'Production': 'https://inspector-ebalance.mof.gov.mn'
		};
		
		frm.set_value('auth_url', auth_urls[frm.doc.environment] || auth_urls['Staging']);
		frm.set_value('api_url', api_urls[frm.doc.environment] || api_urls['Staging']);
		
		// Clear connection status when environment changes
		frm.set_value('connection_status', '');
		frm.set_value('per_map_user_role_id', '');
	},
	
	test_connection_button: function(frm) {
		frm.call('test_connection').then(r => {
			frm.reload_doc();
		});
	},
	
	username: function(frm) {
		// Auto-fill user_regno if empty
		if (!frm.doc.user_regno && frm.doc.username) {
			frm.set_value('user_regno', frm.doc.username);
		}
	}
});

// Helper function to show mapping preview dialog
function show_mapping_preview(results) {
	let matched_html = '';
	let unmatched_html = '';
	
	// Build matched accounts table
	if (results.matched && results.matched.length > 0) {
		matched_html = `
			<h5>Can be auto-mapped (${results.matched.length})</h5>
			<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th>ERPNext Account</th>
						<th>MOF Code</th>
					</tr>
				</thead>
				<tbody>
					${results.matched.slice(0, 20).map(m => `
						<tr>
							<td>${m.account_name || m.account}</td>
							<td>${m.mof_code}</td>
						</tr>
					`).join('')}
					${results.matched.length > 20 ? `<tr><td colspan="2">... and ${results.matched.length - 20} more</td></tr>` : ''}
				</tbody>
			</table>
		`;
	}
	
	// Build unmatched accounts table
	if (results.unmatched && results.unmatched.length > 0) {
		unmatched_html = `
			<h5>Need manual mapping (${results.unmatched.length})</h5>
			<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th>ERPNext Account</th>
						<th>Suggested MOF Codes</th>
					</tr>
				</thead>
				<tbody>
					${results.unmatched.slice(0, 20).map(m => `
						<tr>
							<td>${m.account_name || m.account}</td>
							<td>${m.suggestions && m.suggestions.length > 0 
								? m.suggestions.slice(0, 3).map(s => s.mof_code).join(', ')
								: 'No suggestions'}</td>
						</tr>
					`).join('')}
					${results.unmatched.length > 20 ? `<tr><td colspan="2">... and ${results.unmatched.length - 20} more</td></tr>` : ''}
				</tbody>
			</table>
		`;
	}
	
	frappe.msgprint({
		title: __('Auto-Mapping Preview'),
		message: matched_html + unmatched_html,
		indicator: 'blue',
		wide: true
	});
}
