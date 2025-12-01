import unittest
import os
import sys
import json
import shutil

# Ensure the root directory is in the path so we can import verify_field
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from verify_field import verify_field

class TestVerifyField(unittest.TestCase):
    def setUp(self):
        # Path to the repo sample PDF
        self.repo_pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'sample_declaration.pdf')

        if not os.path.exists(self.repo_pdf_path):
            self.skipTest(f"Sample PDF not found at {self.repo_pdf_path}")

        # Create a temporary copy to avoid modifying/corrupting the original during tests
        self.temp_dir = 'tests/temp_data'
        os.makedirs(self.temp_dir, exist_ok=True)
        self.pdf_path = os.path.join(self.temp_dir, 'test_sample.pdf')

        # Copy from repo sample to temp location
        shutil.copy(self.repo_pdf_path, self.pdf_path)

        self.page_number = 1
        self.model = "qwen3-vl:32b" # Using the model that worked

    def tearDown(self):
        # Clean up temp file
        if os.path.exists(self.pdf_path):
            os.remove(self.pdf_path)
        if os.path.exists(self.temp_dir):
            try:
                os.rmdir(self.temp_dir)
            except OSError:
                pass

    def test_verify_consignor(self):
        field_name = "parties.consignor.name"
        expected_value = "开平市世华纪元经贸有限公司"

        result = verify_field(self.pdf_path, self.page_number, field_name, self.model)

        self.assertIsNotNone(result, "Result should not be None")
        self.assertIn("value", result, "Result should contain 'value' key")
        # Allow for slight variations (e.g. inclusion of IDs)
        self.assertIn(expected_value, result["value"])

    def test_verify_consignee(self):
        field_name = "parties.consignee"
        expected_value = "RETAIL HOLDINGS PTY LIMITED"

        result = verify_field(self.pdf_path, self.page_number, field_name, self.model)

        self.assertIsNotNone(result, "Result should not be None")
        self.assertEqual(result["value"], expected_value)

    def test_verify_destination_port(self):
        field_name = "logistics.destination_port"
        expected_value = "澳大利亚"

        result = verify_field(self.pdf_path, self.page_number, field_name, self.model)

        self.assertIsNotNone(result, "Result should not be None")
        self.assertEqual(result["value"], expected_value)

if __name__ == '__main__':
    unittest.main()
