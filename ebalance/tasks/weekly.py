# Copyright (c) 2025, MN Frappe and contributors
# For license information, please see license.txt
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportArgumentType=false

"""
eBalance Weekly Scheduled Tasks
Runs every week via Frappe scheduler
"""

import frappe
from frappe.utils import add_days, getdate, now_datetime


def execute():
    """Main weekly task executor"""
    if not is_ebalance_enabled():
        return

    cleanup_old_logs()
    sync_all_periods()
    generate_weekly_report()


def is_ebalance_enabled():
    """Check if eBalance is enabled"""
    try:
        settings = frappe.get_cached_doc("eBalance Settings")
        return settings.enabled == 1
    except Exception:
        return False


def cleanup_old_logs():
    """
    Clean up old submission logs based on retention policy
    """
    try:
        settings = frappe.get_cached_doc("eBalance Settings")
        retention_days = settings.log_retention_days or 90

        cutoff_date = add_days(getdate(), -retention_days)

        # Delete old submission logs
        old_logs = frappe.db.get_all(
            "eBalance Submission Log",
            filters={
                "creation": ["<", cutoff_date]
            },
            pluck="name"
        )

        deleted_count = 0
        for log in old_logs:
            try:
                frappe.delete_doc(
                    "eBalance Submission Log",
                    log,
                    ignore_permissions=True,
                    force=True
                )
                deleted_count += 1
            except Exception:
                pass

        if deleted_count > 0:
            frappe.db.commit()
            frappe.log_error(
                message=f"Cleaned up {deleted_count} old submission logs",
                title="eBalance Log Cleanup"
            )

    except Exception as e:
        frappe.log_error(
            message=f"Log cleanup failed: {e!s}",
            title="eBalance Cleanup Error"
        )


def sync_all_periods():
    """
    Full sync of all report periods
    Runs weekly for comprehensive updates
    """
    try:
        settings = frappe.get_cached_doc("eBalance Settings")

        if not settings.enabled:
            return

        # Only run if auto_sync_interval is Weekly
        if settings.auto_sync_interval != "Weekly":
            return

        from ebalance.api.client import EBalanceClient

        client = EBalanceClient()

        # Get current writing config code from settings
        writing_config_code = settings.writing_config_code if hasattr(settings, 'writing_config_code') else None
        if not writing_config_code:
            return

        # Get all connected periods
        org_list = client.get_report_org_list(writing_config_code)

        if not org_list:
            return

        synced_count = 0

        for org in org_list:
            period_id = org.get("perMapUserRoleId") or org.get("id")

            if not period_id:
                continue

            # Update or create period
            existing = frappe.db.exists(
                "eBalance Report Period",
                {"external_id": str(period_id)}
            )

            if existing:
                doc = frappe.get_doc("eBalance Report Period", existing)
                doc.update({
                    "period_name": org.get("reportName", ""),
                    "status": org.get("status", "Active"),
                    "last_sync": now_datetime()
                })
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({
                    "doctype": "eBalance Report Period",
                    "external_id": str(period_id),
                    "period_name": org.get("reportName", ""),
                    "status": org.get("status", "Active"),
                    "last_sync": now_datetime()
                })
                doc.insert(ignore_permissions=True)
                synced_count += 1

        if synced_count > 0:
            frappe.db.commit()
            frappe.log_error(
                message=f"Weekly sync: {synced_count} new periods",
                title="eBalance Weekly Sync"
            )

    except Exception as e:
        frappe.log_error(
            message=f"Weekly sync failed: {e!s}",
            title="eBalance Weekly Sync Error"
        )


def generate_weekly_report():
    """
    Generate weekly eBalance status report
    Sends summary to administrators
    """
    try:
        settings = frappe.get_cached_doc("eBalance Settings")

        if not settings.enabled:
            return

        # Get statistics
        total_periods = frappe.db.count("eBalance Report Period")
        active_periods = frappe.db.count(
            "eBalance Report Period",
            {"status": "Active"}
        )

        total_requests = frappe.db.count("eBalance Report Request")
        submitted_requests = frappe.db.count(
            "eBalance Report Request",
            {"status": "Submitted"}
        )
        pending_requests = frappe.db.count(
            "eBalance Report Request",
            {"status": ["in", ["Draft", "In Progress", "Pending"]]}
        )

        # Log summary
        summary = f"""
        eBalance Weekly Summary:
        - Total Report Periods: {total_periods}
        - Active Periods: {active_periods}
        - Total Requests: {total_requests}
        - Submitted: {submitted_requests}
        - Pending: {pending_requests}
        """

        frappe.log_error(
            message=summary,
            title="eBalance Weekly Summary"
        )

    except Exception as e:
        frappe.log_error(
            message=f"Weekly report generation failed: {e!s}",
            title="eBalance Weekly Report Error"
        )


def check_api_health():
    """
    Check MOF API health status
    """
    try:
        from ebalance.api.client import EBalanceClient

        client = EBalanceClient()

        # Simple health check - try to get user roles
        start_time = now_datetime()
        roles = client.get_user_roles()
        end_time = now_datetime()

        response_time = (end_time - start_time).total_seconds()

        health_status = {
            "status": "healthy" if roles else "degraded",
            "response_time": response_time,
            "timestamp": str(now_datetime())
        }

        # Store health status
        frappe.cache().set_value(
            "ebalance_api_health",
            health_status,
            expires_in_sec=86400  # 24 hours
        )

        return health_status

    except Exception as e:
        health_status = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(now_datetime())
        }

        frappe.cache().set_value(
            "ebalance_api_health",
            health_status,
            expires_in_sec=86400
        )

        frappe.log_error(
            message=f"API health check failed: {e!s}",
            title="eBalance API Health"
        )

        return health_status
