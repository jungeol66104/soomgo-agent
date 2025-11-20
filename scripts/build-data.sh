#!/usr/bin/env bash
# Build data package for distribution

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}Building Data Package${NC}"
echo "====================="
echo ""

# Check if data directory exists
if [ ! -d "data" ]; then
    echo -e "${RED}Error: data/ directory not found${NC}"
    exit 1
fi

# Create dist directory if it doesn't exist
mkdir -p dist

# Create data package
echo -e "${CYAN}Creating data.tar.gz...${NC}"
echo ""
echo "Including:"
echo "  - data/messages/ (16K+ conversations)"
echo "  - data/chat_list_master.jsonl (chat index)"
echo "  - data/knowledge/ (FAQ & services)"
echo "  - data/prompts/ (prompt templates)"
echo ""

# Create tarball with only essential data
tar -czf dist/data.tar.gz \
    --exclude="data/runs" \
    --exclude="data/simulations" \
    --exclude="data/analysis" \
    --exclude="data/session" \
    --exclude="data/sessions" \
    --exclude="data/shadow" \
    --exclude="data/chatbot_state.json" \
    data/messages \
    data/chat_list_master.jsonl \
    data/knowledge \
    data/prompts

echo -e "${GREEN}✓ Data package created${NC}"
echo ""

# Show size
SIZE=$(du -h dist/data.tar.gz | cut -f1)
echo -e "Package: ${CYAN}dist/data.tar.gz${NC}"
echo -e "Size: ${CYAN}${SIZE}${NC}"
echo ""

# Show contents summary
echo "Contents:"
tar -tzf dist/data.tar.gz | head -10
TOTAL=$(tar -tzf dist/data.tar.gz | wc -l | tr -d ' ')
echo "... (${TOTAL} total files)"
echo ""

echo -e "${GREEN}Ready for distribution!${NC}"
echo ""
