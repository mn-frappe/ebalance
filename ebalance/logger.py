# pyright: reportMissingImports=false
"""
eBalance Logging Utilities

Provides standardized logging for all eBalance actions using Frappe's logging infrastructure.
Logs are stored in:
- Error Log DocType (for errors)
- eBalance Log DocType (for MOF submissions and reports)
- frappe.log file (for debug/info logs)
"""

import frappe
from frappe import _
from typing import Optional, Dict, Any
import json
import traceback
from functools import wraps


# Logger instance for file logging
def get_logger():
    """Get eBalance logger instance."""
    return frappe.logger("ebalance", allow_site=True, file_count=10)


def log_info(message: str, data: Optional[Dict] = None):
    """
    Log info level message.
    
    Args:
        message: Log message
        data: Optional additional data to log
    """
    logger = get_logger()
    if data:
        logger.info(f"{message} | Data: {json.dumps(data, default=str)}")
    else:
        logger.info(message)


def log_debug(message: str, data: Optional[Dict] = None):
    """Log debug level message."""
    logger = get_logger()
    if data:
        logger.debug(f"{message} | Data: {json.dumps(data, default=str)}")
    else:
        logger.debug(message)


def log_warning(message: str, data: Optional[Dict] = None):
    """Log warning level message."""
    logger = get_logger()
    if data:
        logger.warning(f"{message} | Data: {json.dumps(data, default=str)}")
    else:
        logger.warning(message)


def log_error(message: str, data: Optional[Dict] = None, exc: Optional[Exception] = None):
    """
    Log error to both file and Error Log DocType.
    
    Args:
        message: Error message
        data: Optional additional data
        exc: Optional exception object
    """
    logger = get_logger()
    
    error_details = {
        "message": message,
        "data": data,
        "traceback": traceback.format_exc() if exc else None
    }
    
    logger.error(f"{message} | Details: {json.dumps(error_details, default=str)}")
    
    # Also log to Error Log DocType for visibility in UI
    frappe.log_error(
        message=json.dumps(error_details, default=str, indent=2),
        title=f"eBalance: {message[:100]}"
    )


def log_api_call(
    endpoint: str,
    method: str = "POST",
    request_data: Optional[Dict] = None,
    response_data: Optional[Dict] = None,
    status: str = "Success",
    error_message: Optional[str] = None,
    reference_doctype: Optional[str] = None,
    reference_name: Optional[str] = None,
    execution_time: Optional[float] = None
):
    """
    Log API call to eBalance Log DocType.
    
    Args:
        endpoint: API endpoint called
        method: HTTP method (GET, POST, etc.)
        request_data: Request payload
        response_data: Response received
        status: Success/Failed/Error
        error_message: Error message if failed
        reference_doctype: Related DocType
        reference_name: Related document name
        execution_time: Time taken in seconds
    """
    try:
        # Check if eBalance Log DocType exists
        if not frappe.db.exists("DocType", "eBalance Log"):
            # Fall back to file logging
            log_info(f"API Call: {method} {endpoint}", {
                "status": status,
                "reference": f"{reference_doctype}/{reference_name}" if reference_doctype else None,
                "execution_time": execution_time,
                "error": error_message
            })
            return
        
        doc = frappe.get_doc({
            "doctype": "eBalance Log",
            "endpoint": endpoint,
            "method": method,
            "request_data": json.dumps(request_data, default=str) if request_data else None,
            "response_data": json.dumps(response_data, default=str) if response_data else None,
            "status": status,
            "error_message": error_message,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "execution_time": execution_time
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        
    except Exception as e:
        # Don't let logging failures break the main flow
        log_warning(f"Failed to create eBalance Log: {str(e)}")


def log_report(
    action: str,
    report_type: str,
    company: Optional[str] = None,
    fiscal_year: Optional[str] = None,
    period: Optional[str] = None,
    status: str = "Pending",
    submission_id: Optional[str] = None,
    details: Optional[Dict] = None
):
    """
    Log eBalance report event.
    
    Args:
        action: Action performed (generate_report, submit_report, validate, etc.)
        report_type: Type of report (trial_balance, balance_sheet, income_statement, etc.)
        company: Company name
        fiscal_year: Fiscal year
        period: Reporting period (monthly/quarterly)
        status: Report status
        submission_id: MOF submission ID
        details: Additional details
    """
    log_info(f"Report: {action}", {
        "report_type": report_type,
        "company": company,
        "fiscal_year": fiscal_year,
        "period": period,
        "status": status,
        "submission_id": submission_id,
        "details": details
    })
    
    # Also log to Activity Log for audit trail
    try:
        frappe.get_doc({
            "doctype": "Activity Log",
            "subject": f"eBalance {action}: {report_type} - {company}",
            "content": json.dumps({
                "action": action,
                "report_type": report_type,
                "company": company,
                "fiscal_year": fiscal_year,
                "period": period,
                "status": status,
                "submission_id": submission_id,
                "details": details
            }, default=str),
            "reference_doctype": "Company",
            "reference_name": company,
            "status": "Success" if status in ["Submitted", "Success", "Completed", "Approved"] else "Open"
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # Activity log is optional


def log_action(action_name: str):
    """
    Decorator to log function entry/exit and exceptions.
    
    Usage:
        @log_action("Generate Trial Balance")
        def generate_trial_balance(company, period):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            func_name = func.__name__
            
            # Log entry
            logger.debug(f"[{action_name}] Starting {func_name}")
            
            try:
                result = func(*args, **kwargs)
                logger.debug(f"[{action_name}] Completed {func_name}")
                return result
            except Exception as e:
                log_error(f"[{action_name}] Failed in {func_name}: {str(e)}", exc=e)
                raise
        
        return wrapper
    return decorator


def log_scheduler_task(task_name: str):
    """
    Decorator for scheduler tasks with comprehensive logging.
    
    Usage:
        @log_scheduler_task("Auto Generate Monthly Report")
        def auto_generate_monthly():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            log_info(f"Scheduler Task Started: {task_name}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                log_info(f"Scheduler Task Completed: {task_name}", {
                    "execution_time_seconds": round(execution_time, 2),
                    "result": result if isinstance(result, (dict, list, str, int, float, bool)) else str(type(result))
                })
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                log_error(f"Scheduler Task Failed: {task_name}", {
                    "execution_time_seconds": round(execution_time, 2)
                }, exc=e)
                raise
        
        return wrapper
    return decorator


# Convenience functions for common log patterns
def log_trial_balance_generated(company: str, period: str, accounts_count: int):
    """Log trial balance generation."""
    log_report("generate_trial_balance", "Trial Balance", company=company, period=period,
               status="Generated", details={"accounts_count": accounts_count})


def log_balance_sheet_generated(company: str, fiscal_year: str, total_assets: float, total_liabilities: float):
    """Log balance sheet generation."""
    log_report("generate_balance_sheet", "Balance Sheet", company=company, fiscal_year=fiscal_year,
               status="Generated", details={"total_assets": total_assets, "total_liabilities": total_liabilities})


def log_mof_submission(company: str, report_type: str, submission_id: str, status: str):
    """Log MOF submission."""
    log_report("mof_submit", report_type, company=company, status=status, submission_id=submission_id)


def log_gl_aggregation(company: str, period: str, entries_count: int, execution_time: float):
    """Log GL aggregation event."""
    log_info(f"GL Aggregation: {company} - {period}", {
        "entries_count": entries_count,
        "execution_time_seconds": round(execution_time, 2)
    })


def log_cache_operation(operation: str, cache_key: str, hit: bool = False):
    """Log cache operation."""
    log_debug(f"Cache {operation}: {cache_key}", {"hit": hit})
