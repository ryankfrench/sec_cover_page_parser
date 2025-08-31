"""
Setup script for sec_cover_page_parser package.
"""

import os
import re
from setuptools import setup, find_packages

def get_version():
    """Get version from _version.py file."""
    version_file = os.path.join(os.path.dirname(__file__), '_version.py')
    with open(version_file, 'r') as f:
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
        if version_match:
            return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

try:
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    requirements = []

setup(
    name="sec_cover_page_parser",
    version=get_version(),
    author="Ryan French",  # Replace with your actual name
    author_email="rfrench@chapman.edu",  # Replace with your actual email
    description="A package for parsing SEC filing cover pages from XBRL documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ryankfrench/sec_cover_page_parser",  # Replace with your actual GitHub URL
    project_urls={
        "Bug Reports": "https://github.com/ryankfrench/sec_cover_page_parser/issues",
        "Source": "https://github.com/ryankfrench/sec_cover_page_parser",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
        ],
    },
) 