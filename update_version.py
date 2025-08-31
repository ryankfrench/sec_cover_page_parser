#!/usr/bin/env python3
"""
Script to update version in _version.py file.
Usage: python update_version.py <new_version>
"""

import sys
import re

def update_version(new_version):
    """Update version in _version.py file."""
    version_file = '_version.py'
    
    # Read current content
    with open(version_file, 'r') as f:
        content = f.read()
    
    # Update version
    new_content = re.sub(
        r'__version__ = "[^"]*"',
        f'__version__ = "{new_version}"',
        content
    )
    
    # Write back
    with open(version_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Updated version to {new_version} in {version_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        print("Example: python update_version.py 0.1.4")
        sys.exit(1)
    
    new_version = sys.argv[1]
    update_version(new_version)
