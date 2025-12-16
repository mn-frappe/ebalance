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
