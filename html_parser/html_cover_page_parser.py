"""
This module contains functions to parse the coverpage of an XBRL document.
"""

import pathlib
import sys

from bs4 import BeautifulSoup
# import html2text
from text_parser import txt_cover_page_parser as txt_parser

import shutil, subprocess, pathlib

def html_to_text_elinks(html: str, width: int = 70) -> str:
    """Render HTML to plain-text using links/links2 without temporary files."""
    cmd = [
        "elinks",          # use ELinks, superior stdin support
        "-dump",
        "-dump-width", str(width),   # control wrapping width
        "-force-html",               # treat stdin as HTML
        "/dev/stdin"                 # read HTML from stdin
    ]
    return subprocess.check_output(cmd, input=html, text=True)

def html_to_text_html2text(html: str, width: int = 70) -> str:
    h = html2text.HTML2Text()
    h.body_width   = 0          # keep original line lengths – no re-wrapping
    h.unicode_snob = True       # keep “–”, “…” etc. as Unicode
    h.ignore_links = False      # include link targets as footnotes
    return h.handle(html)

def parse_coverpage(html_doc: str):
    txt = html_to_text_elinks(html_doc)

    return txt_parser.parse_txt_filing(txt)

def test_html_parsing():
    with open("test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm", "r") as file:
        html_doc = file.read()
        results = parse_coverpage(html_doc)
        print(results)

if __name__ == "__main__":
    test_html_parsing()
