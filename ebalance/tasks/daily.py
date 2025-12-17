# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
eBalance Daily Scheduled Tasks
Runs every day via Frappe scheduler
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, now_datetime


def execute():
    """Main daily task executor"""
    if not is_ebalance_enabled():
        return

    sync_report_periods()
    check_pending_reports()
    send_deadline_reminders()


def is_ebalance_enabled():
    """Check if eBalance is enabled"""
    try:
        settings = frappe.get_cached_doc("eBalance Settings")
        return settings.enabled == 1 and settings.auto_sync_periods == 1
    except Exception:
        return False


def sync_report_periods():
    """
    Sync available report periods from MOF
    Creates eBalance Report Period records for new periods
    """
    try:
        settings = frappe.get_cached_doc("eBalance Settings")

        if not settings.enabled or settings.auto_sync_interval != "Daily":
            return

        from ebalance.api.client import EBalanceClient

        client = EBalanceClient()

        # Get writing configs (available periods)
        configs = client.get_writing_configs()

        if not configs:
            frappe.log_error(
                message="No report periods returned from MOF",
                title="eBalance Period Sync"
            )
            return

        synced_count = 0

        for config in configs:
            period_id = config.get("id") or config.get("perMapUserRoleId")

            if not period_id:
                continue

            # Check if period already exists
            existing = frappe.db.exists(
                "eBalance Report Period",
                {"external_id": str(period_id)}
            )

            if existing:
                # Update existing period
                doc = frappe.get_doc("eBalance Report Period", existing)
                doc.update({
                    "period_name": config.get("name", config.get("reportName", "")),
                    "status": config.get("status", "Active"),
                    "deadline": config.get("deadline"),
                    "last_sync": now_datetime()
                })
                doc.save(ignore_permissions=True)
            else:
                # Create new period
                doc = frappe.get_doc({
                    "doctype": "eBalance Report Period",
                    "external_id": str(period_id),
                    "period_name": config.get("name", config.get("reportName", "")),
                    "period_start": config.get("startDate"),
                    "period_end": config.get("endDate"),
                    "deadline": config.get("deadline"),
                    "status": config.get("status", "Active"),
                    "period_type": config.get("type", "Monthly"),
                    "last_sync": now_datetime()
                })
                doc.insert(ignore_permissions=True)
                synced_count += 1

        if synced_count > 0:
            frappe.db.commit()
            frappe.log_error(
                message=f"Synced {synced_count} new report periods",
                title="eBalance Period Sync Success"
            )

    except Exception as e:
        frappe.log_error(
            message=f"Period sync failed: {e!s}",
            title="eBalance Period Sync Error"
        )


def check_pending_reports():
    """
    Check for pending report submissions
    Update status of report requests
    """
    try:
        # Get all pending requests
        pending_requests = frappe.db.get_all(
            "eBalance Report Request",
            filters={
                "status": ["in", ["Draft", "In Progress", "Pending"]]
            },
            fields=["name", "external_id", "period_name"]
        )

        if not pending_requests:
            return

        from ebalance.api.client import EBalanceClient

        client = EBalanceClient()

        for request in pending_requests:
            if not request.external_id:
                continue

            try:
                # Check status on MOF side
                report_data = client.get_report_data(
                    request.external_id,
                    None  # org_id from settings
                )

                if report_data:
                    status = report_data.get("status", "")

                    # Update local status
                    if status == "CONFIRMED":
                        frappe.db.set_value(
                            "eBalance Report Request",
                            request.name,
                            "status",
                            "Submitted"
                        )
                    elif status == "REJECTED":
                        frappe.db.set_value(
                            "eBalance Report Request",
                            request.name,
                            "status",
                            "Error"
                        )

            except Exception as e:
                frappe.log_error(
                    message=f"Status check failed for {request.name}: {e!s}",
                    title="eBalance Status Check Error"
                )

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            message=f"Pending report check failed: {e!s}",
            title="eBalance Pending Check Error"
        )


def send_deadline_reminders():
    """
    Send reminders for upcoming report deadlines
    """
    try:
        settings = frappe.get_cached_doc("eBalance Settings")

        if not settings.enabled:
            return

        # Get periods with deadline in next 7 days
        upcoming_deadlines = frappe.db.get_all(
            "eBalance Report Period",
            filters={
                "status": "Active",
                "deadline": ["between", [getdate(), add_days(getdate(), 7)]]
            },
            fields=["name", "period_name", "deadline"]
        )

        if not upcoming_deadlines:
            return

        # Check for unsubmitted reports
        for period in upcoming_deadlines:
            pending = frappe.db.exists(
                "eBalance Report Request",
                {
                    "period_name": period.period_name,
                    "status": ["not in", ["Submitted", "Confirmed"]]
                }
            )

            if pending or not frappe.db.exists(
                "eBalance Report Request",
                {"period_name": period.period_name}
            ):
                # Send notification to Accounts Managers
                users = frappe.db.get_all(
                    "Has Role",
                    filters={"role": "Accounts Manager"},
                    pluck="parent"
                )

                for user in users:
                    try:
                        frappe.publish_realtime(
                            "msgprint",
                            {
                                "message": _(
                                    "eBalance Report '{0}' deadline is {1}"
                                ).format(period.period_name, period.deadline),
                                "indicator": "orange",
                                "title": _("eBalance Deadline Reminder")
                            },
                            user=user
                        )
                    except Exception:
                        pass

    except Exception as e:
        frappe.log_error(
            message=f"Deadline reminder failed: {e!s}",
            title="eBalance Reminder Error"
        )
