"""
Example usage of the XBRL Parser.

This script demonstrates how to use the XBRL cover page parser
to extract information from SEC filing documents.
"""

import os

from xbrl_parser.xbrl_cover_page_parser import parse_coverpage, has_xbrl


def main():
    """Example usage of the XBRL parser."""
    
    # Example file path - adjust as needed
    test_file_path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    
    if not os.path.exists(test_file_path):
        print(f"Test file not found: {test_file_path}")
        print("Please ensure the test file exists or update the path.")
        return
    
    # Read the HTML document
    with open(test_file_path, "r") as file:
        html_doc = file.read()
    
    # Check if the document contains XBRL data
    if has_xbrl(html_doc):
        print("✓ Document contains XBRL data")
        
        # Parse the cover page
        results = parse_coverpage(html_doc)
        
        # Display the results
        print("\n=== Parsed Filing Information ===")
        print(f"Company Name: {results.company_name}")
        print(f"Document Type: {results.document_type}")
        print(f"Address: {results.document_address}")
        print(f"ZIP Code: {results.document_zip}")
        print(f"State of Incorporation: {results.state_of_incorporation}")
        print(f"IRS Number: {results.irs_number}")
        print(f"Commission File Number: {results.commission_file_number}")
        
    else:
        print("✗ Document does not contain XBRL data")


if __name__ == "__main__":
    main() 