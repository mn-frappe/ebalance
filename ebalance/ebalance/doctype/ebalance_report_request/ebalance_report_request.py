# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
eBalance Report Request - Complete workflow for MOF financial report submission

Workflow:
1. Create Request - Select company, fiscal year, and report period
2. Generate Data - Transform ERPNext GL Entries to MOF format
3. Preview - Review Balance Sheet (СБТ) and Income Statement (ОҮТ)
4. Internal Approval - Review → Approve by CFO/CEO
5. Save Draft - Send data to eBalance for validation
6. Submit - Final submission to MOF for approval
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class eBalanceReportRequest(Document):
    """
    eBalance Report Request DocType

    Manages the complete lifecycle of a financial report submission:
    - Draft: Initial creation
    - Generating: Report data being generated from ERPNext
    - Ready: Data generated, ready for submission
    - In Progress: Saved to eBalance, pending submission
    - Submitted: Sent to MOF for approval
    - Confirmed: Approved by MOF
    - Rejected: Rejected by MOF
    - Failed: Error during process

    Workflow States (internal approval):
    - Draft: Initial state
    - Ready for Review: Report generated, pending accountant review
    - Pending Review: Submitted for reviewer check
    - Pending Approval: Reviewed, awaiting CFO/CEO approval
    - Approved: Ready for MOF submission
    - Rejected: Returned for corrections
    - Submitted to MOF: Sent to government
    - Confirmed: Confirmed by MOF
    """

    def validate(self):
        """Validate report request"""
        self.validate_dates()
        self.validate_company()
        self.set_defaults()

    def before_save(self):
        """Track workflow state changes for audit log"""
        if self.has_value_changed("workflow_state"):
            self._log_workflow_change()

    def _log_workflow_change(self):
        """Log workflow state changes"""
        old_state = self.get_doc_before_save()
        old_workflow_state = old_state.workflow_state if old_state else None
        new_workflow_state = self.workflow_state

        if old_workflow_state == new_workflow_state:
            return

        # Determine action from state change
        action = self._get_action_from_state_change(old_workflow_state, new_workflow_state)

        # Update approval fields based on workflow action
        if new_workflow_state == "Pending Approval":
            self.reviewed_by = frappe.session.user
            self.reviewed_date = now_datetime()
        elif new_workflow_state == "Approved":
            self.approved_by = frappe.session.user
            self.approved_date = now_datetime()

        # Create approval log
        from ebalance.ebalance.doctype.ebalance_approval_log.ebalance_approval_log import (
            create_approval_log,
        )
        create_approval_log(
            report_request=self.name,
            action=action,
            from_status=old_workflow_state,
            to_status=new_workflow_state,
            comments=self.approval_comments
        )

    def _get_action_from_state_change(self, old_state, new_state):
        """Determine action name from state transition"""
        transitions = {
            ("Draft", "Ready for Review"): "Created",
            ("Ready for Review", "Pending Review"): "Submitted for Review",
            ("Pending Review", "Pending Approval"): "Reviewed",
            ("Pending Approval", "Approved"): "Approved",
            ("Pending Review", "Rejected"): "Rejected",
            ("Pending Approval", "Rejected"): "Rejected",
            ("Rejected", "Draft"): "Created",
            ("Approved", "Submitted to MOF"): "Submitted to MOF",
            ("Submitted to MOF", "Confirmed"): "Confirmed by MOF",
        }
        return transitions.get((old_state, new_state), f"Changed to {new_state}")

    def validate_dates(self):
        """Validate from_date and to_date"""
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                frappe.throw(_("From Date cannot be after To Date"))

    def validate_company(self):
        """Validate company has eBalance enabled"""
        if self.company:
            ebalance_enabled = frappe.db.get_value(
                "Company", self.company, "ebalance_enabled"
            )
            if not ebalance_enabled:
                frappe.msgprint(
                    _("eBalance reporting is not enabled for {0}. Enable it in Company settings.").format(
                        self.company
                    ),
                    indicator="orange"
                )

    def set_defaults(self):
        """Set default values from fiscal year if not set"""
        if self.fiscal_year and not (self.from_date and self.to_date):
            fy = frappe.get_doc("Fiscal Year", self.fiscal_year)
            self.from_date = self.from_date or fy.year_start_date
            self.to_date = self.to_date or fy.year_end_date

    @frappe.whitelist()
    def generate_report_data(self):
        """
        Generate report data from ERPNext GL Entries.

        Uses MOF Account Mappings to transform trial balance
        to eBalance format (СБТ, ОҮТ forms).
        """
        self.status = "Generating"
        self.save()

        try:
            from ebalance.api.transformer import preview_balance_sheet

            # Generate Balance Sheet preview
            bs_result = preview_balance_sheet(
                company=self.company,
                from_date=str(self.from_date),
                to_date=str(self.to_date)
            )

            self.balance_sheet_preview = frappe.as_json(bs_result.get("data", []))

            # Build summary
            summary = bs_result.get("summary", {})
            self.report_summary = """
Balance Sheet Summary:
- Total Assets: {total_assets:,.2f}
- Total Liabilities: {total_liabilities:,.2f}
- Total Equity: {total_equity:,.2f}
- Balance Check: {balance_check:,.2f}
- Is Balanced: {is_balanced}
""".format(**summary)

            self.status = "Ready"
            self.save()

            frappe.msgprint(
                _("Report data generated successfully. Review the preview and submit when ready."),
                indicator="green",
                title=_("Report Generated")
            )

            return {
                "success": True,
                "summary": summary,
                "data": bs_result
            }

        except Exception as e:
            self.status = "Failed"
            self.validation_errors = frappe.as_json({"error": str(e)})
            self.save()

            frappe.throw(
                _("Failed to generate report data: {0}").format(str(e)),
                title=_("Generation Failed")
            )

    @frappe.whitelist()
    def save_to_ebalance(self):
        """
        Save report data to eBalance (draft mode).

        This sends data to MOF eBalance system for validation
        before final submission.
        """
        if self.status not in ["Ready", "In Progress"]:
            frappe.throw(_("Report must be in Ready status to save to eBalance"))

        if not self.report_user_org_hdr_id:
            frappe.throw(_("Report Request ID from eBalance is required"))

        try:
            from ebalance.api.client import get_client
            from ebalance.api.transformer import ReportTransformer

            client = get_client()

            # Initialize transformer with cell IDs from eBalance
            transformer = ReportTransformer(
                company=self.company,
                from_date=str(self.from_date),
                to_date=str(self.to_date)
            )

            # Get report structure from eBalance (includes cell IDs)
            report_period = frappe.get_doc("eBalance Report Period", self.report_period)
            report_data = client.get_report_data(
                report_writing_config_id=report_period.report_writing_config_id,
                report_user_org_hdr_id=self.report_user_org_hdr_id
            )

            # Load cell IDs into transformer
            transformer.load_cell_ids(report_data)

            # Get submission data
            submission_data = transformer.get_submission_data(
                int(self.report_user_org_hdr_id)
            )

            # Save to eBalance
            result = client.save_report_data(
                int(self.report_user_org_hdr_id),
                submission_data.get("cellModelList", [])
            )

            client.close()

            self.status = "In Progress"
            self.save()

            frappe.msgprint(
                _("Report data saved to eBalance successfully. You can now submit for approval."),
                indicator="green",
                title=_("Saved to eBalance")
            )

            return {"success": True, "result": result}

        except Exception as e:
            self.validation_errors = frappe.as_json({"error": str(e)})
            self.save()

            frappe.throw(
                _("Failed to save to eBalance: {0}").format(str(e)),
                title=_("Save Failed")
            )

    @frappe.whitelist()
    def submit_report(self):
        """
        Submit report to MOF for final approval.

        This is the final step - once submitted, the report
        goes to MOF inspectors for review and CEO approval.

        REQUIRES: Report must be approved via workflow before submission.
        """
        # Check workflow approval
        if self.workflow_state and self.workflow_state != "Approved":
            frappe.throw(
                _("Report must be approved before submission to MOF. Current state: {0}").format(
                    self.workflow_state
                ),
                title=_("Approval Required")
            )

        if self.status not in ["Ready", "In Progress"]:
            frappe.throw(_("Report must be in Ready or In Progress status to submit"))

        if not self.report_user_org_hdr_id:
            frappe.throw(_("Report Request ID from eBalance is required"))

        try:
            from ebalance.api.client import get_client
            from ebalance.ebalance.doctype.ebalance_approval_log.ebalance_approval_log import (
                create_approval_log,
            )

            client = get_client()

            # Submit to eBalance
            result = client.send_report(int(self.report_user_org_hdr_id))

            client.close()

            # Check for validation errors
            valid_exp_keys = result.get("validExpKeys", [])
            valid_cell_keys = result.get("validCellKeys", [])

            if valid_exp_keys or valid_cell_keys:
                self.status = "Failed"
                self.validation_errors = frappe.as_json({
                    "validExpKeys": valid_exp_keys,
                    "validCellKeys": valid_cell_keys
                })
                self.save()

                frappe.throw(
                    _("Report submission failed validation. Check validation errors for details."),
                    title=_("Validation Failed")
                )

            # Success
            old_status = self.status
            self.status = "Submitted"
            self.submitted_date = now_datetime()
            self.validation_errors = None
            self.save()

            # Log the submission
            create_approval_log(
                report_request=self.name,
                action="Submitted to MOF",
                from_status=old_status,
                to_status="Submitted",
                comments=f"Report submitted to MOF by {frappe.session.user}"
            )

            frappe.msgprint(
                _("Report submitted to MOF successfully! Awaiting inspector review and CEO approval."),
                indicator="green",
                title=_("Submission Successful")
            )

            return {"success": True, "result": result}

        except Exception as e:
            self.validation_errors = frappe.as_json({"error": str(e)})
            self.save()

            frappe.throw(
                _("Failed to submit report: {0}").format(str(e)),
                title=_("Submission Failed")
            )

    @frappe.whitelist()
    def check_status(self):
        """
        Check report status from eBalance.

        Polls eBalance API to see if report has been confirmed
        or rejected by MOF.
        """
        if self.status not in ["Submitted", "Confirmed", "Rejected"]:
            frappe.throw(_("Report must be in Submitted status to check status"))

        if not self.report_user_org_hdr_id:
            frappe.throw(_("Report Request ID from eBalance is required"))

        try:
            from ebalance.api.client import get_client

            client = get_client()

            # Get report period for config IDs
            report_period = frappe.get_doc("eBalance Report Period", self.report_period)

            # Check status via getReportData
            report_data = client.get_report_data(
                report_writing_config_id=report_period.report_writing_config_id,
                report_user_org_hdr_id=self.report_user_org_hdr_id
            )

            client.close()

            # Check for confirmation
            reports = report_data.get("reports", [])
            if reports:
                report = reports[0]
                is_confirm = report.get("isConfirm")
                confirmed_date = report.get("confirmedDate")

                if is_confirm == 1 or is_confirm == "1":
                    self.status = "Confirmed"
                    self.is_confirmed = 1
                    if confirmed_date:
                        self.confirmed_date = confirmed_date
                    self.save()

                    frappe.msgprint(
                        _("Report has been confirmed by MOF!"),
                        indicator="green",
                        title=_("Report Confirmed")
                    )
                else:
                    frappe.msgprint(
                        _("Report is still pending approval."),
                        indicator="blue",
                        title=_("Status Check")
                    )

            return {"success": True, "status": self.status}

        except Exception as e:
            frappe.throw(
                _("Failed to check status: {0}").format(str(e)),
                title=_("Status Check Failed")
            )


# Whitelisted API methods

@frappe.whitelist()
def generate_report_data(name):
    """Generate report data for a request"""
    doc = frappe.get_doc("eBalance Report Request", name)
    return doc.generate_report_data()


@frappe.whitelist()
def save_to_ebalance(name):
    """Save report data to eBalance"""
    doc = frappe.get_doc("eBalance Report Request", name)
    return doc.save_to_ebalance()


@frappe.whitelist()
def submit_report(name):
    """Submit report to MOF"""
    doc = frappe.get_doc("eBalance Report Request", name)
    return doc.submit_report()


@frappe.whitelist()
def check_status(name):
    """Check report status from eBalance"""
    doc = frappe.get_doc("eBalance Report Request", name)
    return doc.check_status()


@frappe.whitelist()
def create_request_from_period(report_period, company):
    """
    Create a new report request from a report period.

    Args:
        report_period: eBalance Report Period name
        company: Company name

    Returns:
        str: Name of created eBalance Report Request
    """
    period = frappe.get_doc("eBalance Report Period", report_period)

    # Get fiscal year from dates
    fiscal_year = frappe.db.get_value(
        "Fiscal Year",
        {
            "year_start_date": ("<=", period.begin_date),
            "year_end_date": (">=", period.end_date)
        },
        "name"
    )

    doc = frappe.new_doc("eBalance Report Request")
    doc.report_period = report_period
    doc.report_user_org_hdr_id = period.report_user_org_hdr_id
    doc.company = company
    doc.fiscal_year = fiscal_year
    doc.from_date = period.begin_date
    doc.to_date = period.end_date
    doc.begin_date = period.begin_date
    doc.end_date = period.end_date
    doc.report_type = period.report_type
    doc.status = "Draft"
    doc.insert()

    return doc.name
