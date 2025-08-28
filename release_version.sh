#!/bin/bash

# Script to create a new version release for GitHub repository

set -e

if [ -z "$1" ]; then
    echo "❌ Error: Please provide a version number"
    echo "Usage: ./release_version.sh <version>"
    echo "Example: ./release_version.sh 0.1.2"
    exit 1
fi

VERSION=$1
TAG="v$VERSION"

echo "🚀 Creating release for version $VERSION..."

# Update version in setup.py
echo "📝 Updating version in setup.py..."
sed -i "s/version=\"[^\"]*\"/version=\"$VERSION\"/" setup.py

# Commit the version change
echo "💾 Committing version change..."
git add setup.py
git commit -m "Bump version to $VERSION"

# Create and push tag
echo "🏷️  Creating tag $TAG..."
git tag $TAG
git push origin main
git push origin $TAG

echo "✅ Successfully created release $TAG!"
echo "📋 Users can now install with:"
echo "   pip install git+https://github.com/ryankfrench/sec_cover_page_parser.git@$TAG"
echo ""
echo "💡 Don't forget to create a GitHub release for $TAG with release notes!"
