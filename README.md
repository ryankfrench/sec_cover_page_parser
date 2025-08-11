# SEC Cover Page Parser

This goal of this project is to accurately parse company information from the cover page of SEC filings. Of specific interest is the company address since it often does not match the address listed in the header.

## Installation

### From Git Repository (Recommended)
```bash
pip install git+https://github.com/yourusername/sec_cover_page_parser.git
```

### From Local Development
```bash
# Clone the repository
git clone https://github.com/yourusername/sec_cover_page_parser.git
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
from text_parser import UnifiedDocumentParser

# Create parser instance
parser = UnifiedDocumentParser()

# Parse a document
result = parser.parse_document(content)

# Access parsed information
print(f"Company: {result.company_name}")
print(f"Address: {result.address}")
print(f"CIK: {result.cik}")
```

### Advanced Usage
```python
from text_parser import (
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
git clone https://github.com/yourusername/sec_cover_page_parser.git
cd sec_cover_page_parser
pip install -e .

# Install additional development tools (optional)
pip install pytest black flake8 mypy
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
