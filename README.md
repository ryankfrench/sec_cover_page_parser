# SEC Cover Page Parser

This goal of this project is to accurately parse company information from the cover page of SEC filings. Of specific interest is the company address since it often does not match the address listed in the header.

## Installation

### From GitHub Packages (Recommended)
```bash
pip install git+https://github.com/ryankfrench/sec_cover_page_parser.git
```

### From Local Development
```bash
# Clone the repository
git clone https://github.com/ryankfrench/sec_cover_page_parser.git
cd sec_cover_page_parser

# Install in development mode
pip install -e .
```

### Dependencies
The parser logic will be like this:

1. check for xbrl data: If exists parse the data from the xbrl markup.
2. check for html data: If exists parse the data from the html markup.

## Usage

### Basic Usage
```python
# When installed from GitHub, you can import directly
from sec_cover_page_parser import parse_coverpage, FilingData, Address

# For XBRL parsing
result = parse_coverpage(xbrl_content)

# Access parsed information
print(f"Company: {result.company_name}")
print(f"Address: {result.document_address}")
print(f"CIK: {result.cik}")

# You can also import specific modules
from sec_cover_page_parser.xbrl_parser.xbrl_cover_page_parser import parse_coverpage
from sec_cover_page_parser.text_parser.txt_cover_page_parser import parse_txt_filing
```

### Advanced Usage
```python
# Import specific modules for advanced usage
from sec_cover_page_parser.xbrl_parser.xbrl_cover_page_parser import parse_coverpage, has_xbrl
from sec_cover_page_parser.text_parser.txt_cover_page_parser import parse_txt_filing
from sec_cover_page_parser.models.filing_data import FilingData
from sec_cover_page_parser.models.address import Address, AddressType

# Parse different document formats
xbrl_result = parse_coverpage(xbrl_content)
text_result = parse_txt_filing(text_content)

# Create data structures
filing_data = FilingData()
address = Address(address_line1="123 Main St", city="New York", state="NY")
```

## Development

### Setup Development Environment
```bash
# Clone and install in development mode
git clone https://github.com/ryankfrench/sec_cover_page_parser.git
cd sec_cover_page_parser
pip install -e .

# Install additional development tools (optional)
pip install pytest black flake8 mypy
```

### Publishing New Versions

To release a new version:

1. **Use the release script** (recommended):
   ```bash
   ./release_version.sh 0.1.2
   ```

2. **Or manually**:
   - Update the version number in `_version.py`
   - Commit and push your changes
   - Create a git tag: `git tag v0.1.2`
   - Push the tag: `git push origin v0.1.2`
   - Create a GitHub release with release notes

**Note**: The version is now managed in a single location (`_version.py`) and automatically imported by both `setup.py` and the package's `__init__.py` file.

**Installation Options:**
```bash
# Install latest version from main branch
pip install git+https://github.com/ryankfrench/sec_cover_page_parser.git

# Install specific version
pip install git+https://github.com/ryankfrench/sec_cover_page_parser.git@v0.1.1

# Install from specific branch
pip install git+https://github.com/ryankfrench/sec_cover_page_parser.git@develop
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
