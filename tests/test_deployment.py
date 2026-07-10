import unittest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.utils.security import security_manager
from core.utils.health import health_engine
from core.utils.crash import crash_manager
from core.database.db import db_manager

class TestDeploymentEngine(unittest.TestCase):

    def test_security_encryption_decryption(self):
        """Tests that sensitive keys are successfully encrypted/decrypted."""
        secret_key = "sk-openrouter-dummy-auth-key-12345"
        
        # Encrypt
        cipher = security_manager.encrypt(secret_key)
        self.assertNotEqual(cipher, secret_key)
        
        # Decrypt
        plain = security_manager.decrypt(cipher)
        self.assertEqual(plain, secret_key)

    def test_health_checks_diagnostics(self):
        """Tests that the health diagnostics checks run successfully."""
        report = health_engine.run_health_checks()
        
        self.assertIn("operating_system", report)
        self.assertIn("python_version", report)
        self.assertIn("storage_writeable", report)

    def test_database_index_optimization(self):
        """Tests executing database vaccum optimization routines."""
        success = db_manager.optimize_database()
        self.assertTrue(success)

    def test_crash_report_capturing(self):
        """Tests generating and listing JSON crash dump files."""
        report_path = ""
        try:
            # Raise mock exception
            raise ValueError("Test diagnostics stack trace")
        except ValueError as err:
            exc_type, exc_val, exc_tb = sys.exc_info()
            report_path = crash_manager.generate_report(exc_type, exc_val, exc_tb)
            
        self.assertTrue(os.path.exists(report_path))
        
        # Read back
        reports = crash_manager.list_reports()
        self.assertTrue(any(r["error_message"] == "Test diagnostics stack trace" for r in reports))
        
        # Clean up report
        if os.path.exists(report_path):
            os.remove(report_path)

if __name__ == "__main__":
    unittest.main()
