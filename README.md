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
from sec_cover_page_parser import parse_coverpage, UnifiedDocumentParser, FilingData

# For XBRL parsing
result = parse_coverpage(xbrl_content)

# For general document parsing
parser = UnifiedDocumentParser()
result = parser.parse_document(content)

# Access parsed information
print(f"Company: {result.company_name}")
print(f"Address: {result.document_address}")
print(f"CIK: {result.cik}")
```

### Advanced Usage
```python
# Import specific modules for advanced usage
from sec_cover_page_parser.text_parser import (
    UnifiedDocumentParser,
    MarkdownCoverPageParser,
    EnhancedTextCoverPageParser,
    HTMLCoverPageParser
)

# Use specific parsers for different document types
markdown_parser = MarkdownCoverPageParser()
text_parser = EnhancedTextCoverPageParser()
html_parser = HTMLCoverPageParser()

# Parse different document formats
markdown_result = markdown_parser.parse(content)
text_result = text_parser.parse(content)
html_result = html_parser.parse(content)
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
   - Update the version number in `setup.py`
   - Commit and push your changes
   - Create a git tag: `git tag v0.1.2`
   - Push the tag: `git push origin v0.1.2`
   - Create a GitHub release with release notes

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
