import argparse
import requests
import os

def extract_filename(file_content):
    """
    Extracts the filename that appears after <FILENAME> tag in the text.
    
    Args:
        file_content (str): The content of the SEC filing as a string
        
    Returns:
        str: The extracted filename or None if not found
    """
    import re
    
    # Search for <FILENAME> followed by any characters until a newline
    match = re.search(r'<FILENAME>(.*?)[\r\n]', file_content)
    
    if match:
        return match.group(1).strip()
    return None

def download_filing(cik: int, accession: str, user_agent: str = 'Your Name your_email@address.com'):
    # Format CIK and accession number
    accession = accession.replace('-', '')
    
    # Define base URL for SEC EDGAR
    base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}"
    
    # Define headers with User-Agent
    headers = {
        'User-Agent': user_agent
    }

    # Create formatted accession with dashes
    acc_with_dashes = f"{accession[0:10]}-{accession[10:12]}-{accession[12:]}"

    # Define file URLs
    filing_txt_url = f"{base_url}/{accession}/{acc_with_dashes}.txt"
    index_url = f"{base_url}/{accession}/{acc_with_dashes}-index.html"

    try:

        # Download index
        index_response = requests.get(index_url, headers=headers)
        index_response.raise_for_status()

        # Download main filing txt
        filing_txt_response = requests.get(filing_txt_url, headers=headers)
        filing_txt_response.raise_for_status()

        # Create directory if it doesn't exist
        os.makedirs(f"test_filings/{cik}/{acc_with_dashes}", exist_ok=True)

        # Save files
        with open(f"test_filings/{cik}/{acc_with_dashes}/{acc_with_dashes}.txt", 'wb') as f:
            f.write(filing_txt_response.content)
        
        with open(f"test_filings/{cik}/{acc_with_dashes}/{acc_with_dashes}-index.html", 'wb') as f:
            f.write(index_response.content)

        # Download filing
        filing_name = extract_filename(filing_txt_response.text)
        if filing_name is not None:
            filing_url = f"{base_url}/{accession}/{filing_name}"
            filing_response = requests.get(filing_url, headers=headers)
            filing_response.raise_for_status()

            with open(f"test_filings/{cik}/{acc_with_dashes}/{filing_name}", 'wb') as f:
                f.write(filing_response.content)

        print(f"Successfully downloaded files for accession {acc_with_dashes}")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading files: {e}")

def main():
    parser = argparse.ArgumentParser(description='Download SEC EDGAR filings')
    parser.add_argument('--cik', help='Company CIK number')
    parser.add_argument('--accession', help='Filing accession number')
    parser.add_argument('--user_agent', help='User agent string', default='Your Name your_email@address.com')
    
    args = parser.parse_args()
    download_filing(args.cik, args.accession, args.user_agent)

def test():
    with open("test_filings/southern_co/0000092122-05-000042/0000092122-05-000042.txt", "r") as f:
        data = f.read()
        print(extract_filename(data))

if __name__ == "__main__":
    main()
    # test()