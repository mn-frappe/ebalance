# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3

"""
eBalance eBarimt Integration Tests

Unit tests for the optional eBarimt VAT reconciliation:
- eBarimt availability detection
- VAT data retrieval
- Reconciliation logic

These are pure unit tests that mock Frappe dependencies.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock frappe before importing test modules
mock_frappe = MagicMock()
mock_frappe._dict = dict
mock_frappe.utils.flt = lambda x, precision=None: round(float(x or 0), precision or 2) if precision else float(x or 0)
mock_frappe.utils.getdate = lambda x: x
mock_frappe.utils.formatdate = lambda x: x
mock_frappe._ = lambda x: x
mock_frappe.format_value = lambda x, y: str(x)
sys.modules['frappe'] = mock_frappe
sys.modules['frappe.utils'] = mock_frappe.utils


class TestEBarimtAvailability(unittest.TestCase):
    """Test suite for eBarimt availability detection."""
    
    def test_ebarimt_not_installed(self):
        """Test eBarimt availability when not installed."""
        from ebalance.integrations.ebarimt import is_ebarimt_available
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance"]
        
        result = is_ebarimt_available()
        self.assertFalse(result)
    
    def test_ebarimt_installed_and_enabled(self):
        """Test eBarimt availability when installed and enabled."""
        from ebalance.integrations.ebarimt import is_ebarimt_available
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance", "ebarimt"]
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.get_single_value.return_value = 1
        
        result = is_ebarimt_available()
        self.assertTrue(result)
    
    def test_ebarimt_installed_but_disabled(self):
        """Test eBarimt availability when installed but disabled."""
        from ebalance.integrations.ebarimt import is_ebarimt_available
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance", "ebarimt"]
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.get_single_value.return_value = 0
        
        result = is_ebarimt_available()
        self.assertFalse(result)


class TestEBarimtVATSummary(unittest.TestCase):
    """Test suite for eBarimt VAT summary retrieval."""
    
    def test_vat_summary_unavailable(self):
        """Test VAT summary returns None when eBarimt unavailable."""
        from ebalance.integrations.ebarimt import get_ebarimt_vat_summary
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance"]
        
        result = get_ebarimt_vat_summary("_Test Company", "2024-01-01", "2024-01-31")
        self.assertIsNone(result)
    
    def test_vat_summary_available(self):
        """Test VAT summary when eBarimt is available."""
        from ebalance.integrations.ebarimt import get_ebarimt_vat_summary
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance", "ebarimt"]
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.get_single_value.return_value = 1
        
        mock_frappe.db.sql.side_effect = [
            [{
                "total_vat": 100000,
                "total_amount": 1100000,
                "b2b_vat": 60000,
                "b2c_vat": 40000,
                "receipt_count": 50,
                "return_vat": 5000
            }],
            [
                {"date": "2024-01-15", "vat_amount": 50000, "count": 25},
                {"date": "2024-01-20", "vat_amount": 50000, "count": 25}
            ]
        ]
        
        result = get_ebarimt_vat_summary("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertTrue(result["available"])
        self.assertEqual(result["totals"]["vat_amount"], 100000)
        self.assertEqual(result["totals"]["receipt_count"], 50)
        self.assertEqual(result["breakdown"]["b2b_vat"], 60000)
        self.assertEqual(result["breakdown"]["b2c_vat"], 40000)


class TestVATReconciliation(unittest.TestCase):
    """Test suite for VAT reconciliation logic."""
    
    def setUp(self):
        """Reset mocks before each test."""
        mock_frappe.reset_mock()
        mock_frappe.db.sql.side_effect = None
        mock_frappe.get_all.return_value = []
    
    def test_reconcile_without_ebarimt(self):
        """Test reconciliation without eBarimt."""
        from ebalance.integrations.ebarimt import reconcile_vat
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance"]
        mock_frappe.get_all.return_value = []
        mock_frappe.db.sql.return_value = [[0]]
        
        # Mock GL summary
        with patch("ebalance.integrations.gl_entry.get_gl_summary_for_period") as mock_gl:
            mock_gl.return_value = {}
            
            result = reconcile_vat("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertFalse(result["ebarimt_available"])
        self.assertIn("not available", result.get("message", "").lower())
    
    def test_reconcile_with_match(self):
        """Test reconciliation with matching amounts."""
        from ebalance.integrations.ebarimt import reconcile_vat
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance", "ebarimt"]
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.get_single_value.return_value = 1
        mock_frappe.format_value = lambda x, **kwargs: str(x)
        
        # Create mock receipt result that supports .get() method
        mock_receipt_result = MagicMock()
        mock_receipt_result.get = lambda k, default=None: {
            "total_vat": 100000, 
            "total_amount": 1100000, 
            "b2b_vat": 60000, 
            "b2c_vat": 40000, 
            "receipt_count": 50, 
            "return_vat": 0
        }.get(k, default)
        
        # Mock eBarimt data - db.sql returns list of results
        mock_frappe.db.sql.side_effect = [
            [mock_receipt_result],  # eBarimt summary
            [],  # daily
        ]
        
        with patch("ebalance.integrations.gl_entry.get_gl_summary_for_period") as mock_gl:
            mock_gl.return_value = {}
            
            with patch("ebalance.integrations.ebarimt._calculate_gl_vat") as mock_calc:
                mock_calc.return_value = {
                    "output_vat": 100000,
                    "input_vat": 50000,
                    "net_vat": 50000
                }
                
                with patch("ebalance.integrations.ebarimt._find_specific_discrepancies") as mock_disc:
                    mock_disc.return_value = []
                    
                    result = reconcile_vat("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertTrue(result["reconciled"])
        self.assertEqual(result["comparison"]["difference"], 0)
    
    def test_reconcile_with_discrepancy(self):
        """Test reconciliation with discrepancy."""
        from ebalance.integrations.ebarimt import reconcile_vat
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance", "ebarimt"]
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.get_single_value.return_value = 1
        
        with patch("ebalance.integrations.gl_entry.get_gl_summary_for_period") as mock_gl:
            mock_gl.return_value = {}
            
            with patch("ebalance.integrations.ebarimt._calculate_gl_vat") as mock_calc:
                mock_calc.return_value = {
                    "output_vat": 100000,
                    "input_vat": 50000,
                    "net_vat": 50000
                }
                
                with patch("ebalance.integrations.ebarimt.get_ebarimt_vat_summary") as mock_eb:
                    mock_eb.return_value = {
                        "available": True,
                        "totals": {
                            "vat_amount": 95000,  # Different from GL
                            "total_amount": 1045000,
                            "receipt_count": 48
                        },
                        "breakdown": {}
                    }
                    
                    with patch("ebalance.integrations.ebarimt._find_specific_discrepancies") as mock_disc:
                        mock_disc.return_value = [
                            {
                                "type": "missing_receipt",
                                "description": "Sales Invoice SINV-00001 has no eBarimt receipt",
                                "amount": 5000
                            }
                        ]
                        
                        result = reconcile_vat("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertFalse(result["reconciled"])
        self.assertEqual(result["comparison"]["difference"], 5000)
        self.assertGreater(len(result["discrepancies"]), 0)


class TestGLVATCalculation(unittest.TestCase):
    """Test suite for GL VAT calculation."""
    
    def setUp(self):
        """Reset mocks before each test."""
        mock_frappe.reset_mock()
        mock_frappe.db.sql.side_effect = None
        mock_frappe.get_all.return_value = []
    
    def test_gl_vat_calculation(self):
        """Test GL VAT calculation."""
        from ebalance.integrations.ebarimt import _calculate_gl_vat
        
        # Create mock account objects that support attribute access
        mock_acc1 = MagicMock()
        mock_acc1.name = "Output VAT - TC"
        mock_acc1.account_name = "Output VAT Payable"
        
        mock_acc2 = MagicMock()
        mock_acc2.name = "Input VAT - TC"
        mock_acc2.account_name = "Input VAT Receivable"
        
        mock_frappe.get_all.return_value = [mock_acc1, mock_acc2]
        
        mock_frappe.db.sql.side_effect = [
            [[100000]],  # Output VAT balance (credit)
            [[-50000]]   # Input VAT balance (debit)
        ]
        
        result = _calculate_gl_vat("_Test Company", "2024-01-01", "2024-01-31")
        
        self.assertEqual(result["output_vat"], 100000)
        self.assertEqual(result["input_vat"], 50000)
        self.assertEqual(result["net_vat"], 50000)


class TestGracefulDegradation(unittest.TestCase):
    """Test suite for graceful degradation when eBarimt unavailable."""
    
    def test_receipts_unavailable(self):
        """Test receipts function returns None when unavailable."""
        from ebalance.integrations.ebarimt import get_ebarimt_receipts_for_reconciliation
        
        mock_frappe.get_installed_apps.return_value = ["frappe", "erpnext", "ebalance"]
        
        result = get_ebarimt_receipts_for_reconciliation("_Test", "2024-01-01", "2024-01-31")
        self.assertIsNone(result)
    
    def test_exception_handling(self):
        """Test graceful exception handling."""
        from ebalance.integrations.ebarimt import is_ebarimt_available
        
        mock_frappe.get_installed_apps.side_effect = Exception("Database error")
        
        # Should return False, not raise
        result = is_ebarimt_available()
        self.assertFalse(result)


class TestModuleExports(unittest.TestCase):
    """Test suite for module exports."""
    
    def test_all_exports_callable(self):
        """Test that all exported functions are callable."""
        from ebalance.integrations.ebarimt import (
            is_ebarimt_available,
            get_ebarimt_vat_summary,
            get_ebarimt_receipts_for_reconciliation,
            reconcile_vat,
            get_reconciliation_data,
        )
        
        self.assertTrue(callable(is_ebarimt_available))
        self.assertTrue(callable(get_ebarimt_vat_summary))
        self.assertTrue(callable(get_ebarimt_receipts_for_reconciliation))
        self.assertTrue(callable(reconcile_vat))
        self.assertTrue(callable(get_reconciliation_data))


if __name__ == "__main__":
    unittest.main()
