#!/bin/bash

# Single entry point for versioning and releasing.
# Delegates version logic to update_version.py, then handles git commit/tag/push.

set -e

if [ -z "$1" ]; then
    echo "Usage: ./release_version.sh <major|minor|patch|X.Y.Z>"
    echo ""
    echo "Examples:"
    echo "  ./release_version.sh patch       # 0.4.5 → 0.4.6"
    echo "  ./release_version.sh minor       # 0.4.5 → 0.5.0"
    echo "  ./release_version.sh major       # 0.4.5 → 1.0.0"
    echo "  ./release_version.sh 2.0.0       # Set explicit version"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Update _version.py (skip its internal confirmation — we confirm below)
python "$SCRIPT_DIR/update_version.py" "$1" -y

# Read the resulting version back from the file
VERSION=$(python -c "exec(open('$SCRIPT_DIR/_version.py').read()); print(__version__)")
TAG="v$VERSION"

echo ""
echo "Release plan:"
echo "  Version : $VERSION"
echo "  Tag     : $TAG"
echo "  Actions : git commit, tag, push to origin/main"
echo ""

read -p "Proceed with release? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
    echo "Release cancelled. _version.py has been updated but not committed."
    echo "Run 'git checkout _version.py' to revert."
    exit 0
fi

git add "$SCRIPT_DIR/_version.py"
git commit -m "Bump version to $VERSION"
git tag "$TAG"
git push origin main
git push origin "$TAG"

echo ""
echo "Released $TAG!"
echo "Install with:"
echo "  pip install git+https://github.com/ryankfrench/sec_cover_page_parser.git@$TAG"
echo ""
echo "Don't forget to create a GitHub release for $TAG with release notes."
