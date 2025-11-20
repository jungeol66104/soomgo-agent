#!/usr/bin/env bash
# Soomgo Agent - One-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/USERNAME/soomgo-agent/main/scripts/install.sh | sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
GITHUB_REPO="jungeol66104/soomgo-agent"
VERSION="0.1.0"
PACKAGE_NAME="soomgo_agent-${VERSION}.tar.gz"
DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/download/v${VERSION}/${PACKAGE_NAME}"

# Banner
echo ""
echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}  Soomgo Agent Installer${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"
echo -e "${CYAN}Detected:${NC} ${OS} ${ARCH}"

# Check if running in WezTerm (optional warning)
if [ -z "$WEZTERM_EXECUTABLE" ]; then
    echo -e "${YELLOW}Note:${NC} For best experience, use WezTerm terminal"
    echo "      Download: https://wezfurlong.org/wezterm/"
    echo ""
fi

# Step 1: Check/Install uv
echo -e "${CYAN}Checking for uv package manager...${NC}"

if command -v uv &> /dev/null; then
    echo -e "${GREEN}✓${NC} uv is already installed"
else
    echo -e "${YELLOW}Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"

    if command -v uv &> /dev/null; then
        echo -e "${GREEN}✓${NC} uv installed successfully"
    else
        echo -e "${RED}✗${NC} Failed to install uv"
        echo "Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

# Step 2: Download package
echo ""
echo -e "${CYAN}Downloading Soomgo Agent...${NC}"

TEMP_DIR=$(mktemp -d)
PACKAGE_PATH="${TEMP_DIR}/${PACKAGE_NAME}"

if curl -fsSL "${DOWNLOAD_URL}" -o "${PACKAGE_PATH}"; then
    echo -e "${GREEN}✓${NC} Package downloaded"
else
    echo -e "${RED}✗${NC} Failed to download package"
    echo "URL: ${DOWNLOAD_URL}"
    exit 1
fi

# Step 3: Install package
echo ""
echo -e "${CYAN}Installing Soomgo Agent...${NC}"

if uv tool install "${PACKAGE_PATH}" --force; then
    echo -e "${GREEN}✓${NC} Soomgo Agent installed"
else
    echo -e "${RED}✗${NC} Installation failed"
    exit 1
fi

# Cleanup package temp
rm -rf "${TEMP_DIR}"

# Step 4: Download conversation data
echo ""
echo -e "${CYAN}Downloading conversation data (this may take a few minutes)...${NC}"

DATA_URL="https://github.com/${GITHUB_REPO}/releases/download/v${VERSION}/data.tar.gz"
DATA_TEMP_DIR=$(mktemp -d)
DATA_PATH="${DATA_TEMP_DIR}/data.tar.gz"

if curl -fsSL "${DATA_URL}" -o "${DATA_PATH}"; then
    echo -e "${GREEN}✓${NC} Data downloaded"
else
    echo -e "${RED}✗${NC} Failed to download data"
    echo "URL: ${DATA_URL}"
    echo ""
    echo "You can download data manually later by running:"
    echo "  curl -L ${DATA_URL} | tar -xzf - -C ~/.soomgo/"
    # Don't exit - app still works without data
fi

# Step 5: Extract data
if [ -f "${DATA_PATH}" ]; then
    echo ""
    echo -e "${CYAN}Extracting data...${NC}"

    mkdir -p ~/.soomgo/data

    if tar -xzf "${DATA_PATH}" -C ~/.soomgo/; then
        echo -e "${GREEN}✓${NC} Data extracted to ~/.soomgo/data"
    else
        echo -e "${RED}✗${NC} Failed to extract data"
    fi

    # Cleanup data temp
    rm -rf "${DATA_TEMP_DIR}"
fi

# Step 4: Verify installation
echo ""
echo -e "${CYAN}Verifying installation...${NC}"

if command -v soomgo &> /dev/null; then
    echo -e "${GREEN}✓${NC} soomgo command is available"
    VERSION_OUTPUT=$(soomgo --version 2>&1 || echo "unknown")
    echo -e "${GREEN}✓${NC} Installed: ${VERSION_OUTPUT}"
else
    echo -e "${YELLOW}⚠${NC}  soomgo command not found in PATH"
    echo ""
    echo "Please add this to your shell config (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then restart your terminal or run:"
    echo "  source ~/.zshrc  # or ~/.bashrc"
    echo ""
fi

# Success message
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Get started:"
echo -e "  ${CYAN}soomgo${NC}  - Launch the app"
echo ""
echo "Need help? Visit: https://github.com/${GITHUB_REPO}"
echo ""

# Check if PATH update is needed
SHELL_NAME=$(basename "$SHELL")
case "$SHELL_NAME" in
    bash)
        SHELL_CONFIG="$HOME/.bashrc"
        ;;
    zsh)
        SHELL_CONFIG="$HOME/.zshrc"
        ;;
    fish)
        SHELL_CONFIG="$HOME/.config/fish/config.fish"
        ;;
    *)
        SHELL_CONFIG=""
        ;;
esac

if [ -n "$SHELL_CONFIG" ] && [ -f "$SHELL_CONFIG" ]; then
    if ! grep -q ".local/bin" "$SHELL_CONFIG" 2>/dev/null; then
        echo -e "${YELLOW}Note:${NC} You may need to restart your terminal for 'soomgo' to work"
        echo ""
    fi
fi
