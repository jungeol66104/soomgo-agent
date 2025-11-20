#!/usr/bin/env bash
# Build release package for distribution
# Creates a tarball ready for GitHub Releases

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}Building Soomgo Agent Release Package${NC}"
echo "========================================"
echo ""

# Get version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
echo -e "${CYAN}Version:${NC} $VERSION"

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info

# Build the package
echo -e "${CYAN}Building package with uv...${NC}"
uv build

# Check if build was successful
if [ ! -f "dist/soomgo_agent-${VERSION}.tar.gz" ]; then
    echo -e "${RED}Build failed! Package not found.${NC}"
    exit 1
fi

echo -e "${GREEN}Build successful!${NC}"
echo ""

# Show package info
SIZE=$(du -h "dist/soomgo_agent-${VERSION}.tar.gz" | cut -f1)
echo "App package:"
echo -e "  ${CYAN}dist/soomgo_agent-${VERSION}.tar.gz${NC} (${SIZE})"
echo ""

# Build data package
echo -e "${CYAN}Building data package...${NC}"
./scripts/build-data.sh

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}All packages ready!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Show both packages
APP_SIZE=$(du -h "dist/soomgo_agent-${VERSION}.tar.gz" | cut -f1)
DATA_SIZE=$(du -h "dist/data.tar.gz" | cut -f1)

echo "Packages created:"
echo -e "  1. ${CYAN}dist/soomgo_agent-${VERSION}.tar.gz${NC} (${APP_SIZE}) - Application"
echo -e "  2. ${CYAN}dist/data.tar.gz${NC} (${DATA_SIZE}) - Conversation data"
echo ""

echo "Next steps:"
echo "  1. Create GitHub release: v${VERSION}"
echo "  2. Upload BOTH files:"
echo "     - dist/soomgo_agent-${VERSION}.tar.gz"
echo "     - dist/data.tar.gz"
echo "  3. Update scripts/install.sh with your repo URL (line 13)"
echo "  4. Commit and push to GitHub"
echo "  5. Share install command:"
echo "     curl -fsSL https://raw.githubusercontent.com/USERNAME/soomgo-agent/main/scripts/install.sh | sh"
echo ""
