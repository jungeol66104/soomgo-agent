#!/usr/bin/env python3
"""Entry point for soomgo-dev command."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cli.main import dev_cli

if __name__ == "__main__":
    sys.exit(dev_cli())
