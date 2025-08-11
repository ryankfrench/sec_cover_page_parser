"""
Tests for XBRL Parser functionality.
"""

import os
import unittest

from xbrl_parser.xbrl_cover_page_parser import parse_coverpage, has_xbrl


class TestXBRLParser(unittest.TestCase):
    """Test cases for XBRL parser functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_file_path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    
    def test_parse_coverpage(self):
        """Test parsing of XBRL cover page."""
        if os.path.exists(self.test_file_path):
            with open(self.test_file_path, "r") as file:
                html_doc = file.read()
                results = parse_coverpage(html_doc)
                
                # Basic assertions
                self.assertIsNotNone(results)
                self.assertIsNotNone(results.company_name)
                self.assertIsNotNone(results.document_type)
                print(f"Parsed company: {results.company_name}")
                print(f"Document type: {results.document_type}")
        else:
            self.skipTest(f"Test file not found: {self.test_file_path}")
    
    def test_has_xbrl(self):
        """Test XBRL detection."""
        if os.path.exists(self.test_file_path):
            with open(self.test_file_path, "r") as file:
                html_doc = file.read()
                has_xbrl_content = has_xbrl(html_doc)
                self.assertTrue(has_xbrl_content)
        else:
            self.skipTest(f"Test file not found: {self.test_file_path}")


if __name__ == "__main__":
    unittest.main() 