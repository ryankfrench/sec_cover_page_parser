"""
Setup script for sec_cover_page_parser package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

try:
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    requirements = []

setup(
    name="sec_cover_page_parser",
    version="0.1.2",  # or "0.2.0" for minor updates, "1.0.0" for major releases
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