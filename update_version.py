#!/usr/bin/env python3
"""
Script to update version in _version.py file.
Usage: 
  python update_version.py <new_version>           # Manual version
  python update_version.py major|minor|patch      # Auto-increment
  python update_version.py maj|min|pat            # Short forms
"""

import sys
import re

def parse_version(version_string):
    """Parse version string into components."""
    parts = version_string.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_string}. Expected format: X.Y.Z")
    
    try:
        return [int(part) for part in parts]
    except ValueError:
        raise ValueError(f"Invalid version format: {version_string}. All parts must be integers.")

def increment_version(current_version, update_type):
    """Increment version based on update type."""
    major, minor, patch = parse_version(current_version)
    
    if update_type in ['major', 'maj']:
        major += 1
        minor = 0
        patch = 0
    elif update_type in ['minor', 'min']:
        minor += 1
        patch = 0
    elif update_type in ['patch', 'pat']:
        patch += 1
    else:
        raise ValueError(f"Invalid update type: {update_type}. Use major/minor/patch or maj/min/pat")
    
    return f"{major}.{minor}.{patch}"

def get_current_version():
    """Get current version from _version.py file."""
    version_file = '_version.py'
    
    try:
        with open(version_file, 'r') as f:
            content = f.read()
        
        # Extract version using regex
        match = re.search(r'__version__ = "([^"]*)"', content)
        if match:
            return match.group(1)
        else:
            raise ValueError("Could not find __version__ in _version.py")
    except FileNotFoundError:
        raise FileNotFoundError(f"Version file {version_file} not found")
    except Exception as e:
        raise Exception(f"Error reading version file: {e}")

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

def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python update_version.py <new_version>           # Manual version")
        print("  python update_version.py major|minor|patch      # Auto-increment")
        print("  python update_version.py maj|min|pat            # Short forms")
        print("\nExamples:")
        print("  python update_version.py 0.1.5                  # Set specific version")
        print("  python update_version.py patch                  # Increment patch (0.1.4 → 0.1.5)")
        print("  python update_version.py minor                  # Increment minor (0.1.4 → 0.2.0)")
        print("  python update_version.py major                  # Increment major (0.1.4 → 1.0.0)")
        sys.exit(1)
    
    update_arg = sys.argv[1]
    
    # Check if it's an update type (auto-increment)
    update_types = ['major', 'minor', 'patch', 'maj', 'min', 'pat']
    
    if update_arg in update_types:
        try:
            current_version = get_current_version()
            print(f"Current version: {current_version}")
            
            new_version = increment_version(current_version, update_arg)
            print(f"New version: {new_version}")
            
            # Ask for confirmation
            response = input(f"Update version from {current_version} to {new_version}? (y/N): ")
            if response.lower() in ['y', 'yes']:
                update_version(new_version)
            else:
                print("Version update cancelled.")
                sys.exit(0)
                
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        # Manual version specification
        new_version = update_arg
        try:
            # Validate version format
            parse_version(new_version)
            update_version(new_version)
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
