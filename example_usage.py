#!/usr/bin/env python3
"""
Example usage of the sec-cover-page-parser package.
This script demonstrates how to use the parser in another project.
"""

from sec_cover_page_parser import parse_coverpage, FilingData

def main():
    # Example SEC filing content (you would load this from a file or API)
    sample_content = """
    SECURITIES AND EXCHANGE COMMISSION
    Washington, D.C. 20549
    
    FORM 10-K
    
    (Mark One)
    [X] ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
    
    For the fiscal year ended December 31, 2023
    
    [ ] TRANSITION REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
    
    Commission file number: 001-00001
    
    APPLE INC.
    (Exact name of registrant as specified in its charter)
    
    Delaware                          001-00001                94-2404110
    (State or other jurisdiction      (Commission File Number) (IRS Employer
    of incorporation or organization)                          Identification No.)
    
    1 Infinite Loop
    Cupertino, California 95014
    (Address of principal executive offices) (Zip Code)
    
    Registrant's telephone number, including area code: (408) 996-1010
    
    Securities registered pursuant to Section 12(b) of the Act:
    
    Title of each class                    Trading Symbol(s)    Name of each exchange on which registered
    Common Stock, $0.00001 par value       AAPL                 NASDAQ Global Select Market
    
    Securities registered pursuant to Section 12(g) of the Act: None
    
    Indicate by check mark if the registrant is a well-known seasoned issuer, as defined in Rule 405 of the Securities Act.
    [X] Yes  [ ] No
    
    Indicate by check mark if the registrant is not required to file reports pursuant to Section 13 or Section 15(d) of the Act.
    [ ] Yes  [X] No
    """
    
    # Parse the document
    print("Parsing SEC filing content...")
    result = parse_coverpage(sample_content)
    
    # Display results
    print("\n=== Parsed Information ===")
    print(f"Company Name: {result.company_name}")
    print(f"Address: {result.address}")
    print(f"CIK: {result.cik}")
    print(f"File Number: {result.file_number}")
    print(f"State: {result.state}")
    print(f"Phone: {result.phone}")
    print(f"Document Type: {result.document_type}")
    
    # Show all extracted entities
    if hasattr(result, 'entities') and result.entities:
        print(f"\n=== Extracted Entities ===")
        for entity in result.entities:
            print(f"- {entity.type}: {entity.text} (confidence: {entity.confidence:.2f})")

if __name__ == "__main__":
    main() 