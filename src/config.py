"""Configuration management for vf-data scraper."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SESSION_DIR = DATA_DIR / "session"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

# Soomgo credentials
SOOMGO_EMAIL = os.getenv("SOOMGO_EMAIL")
SOOMGO_PASSWORD = os.getenv("SOOMGO_PASSWORD")

# Browser settings
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

# Session file path
SESSION_FILE = SESSION_DIR / "soomgo_session.json"


def validate_config():
    """Validate that required configuration is present."""
    if not SOOMGO_EMAIL or not SOOMGO_PASSWORD:
        raise ValueError(
            "Missing credentials! Please set SOOMGO_EMAIL and SOOMGO_PASSWORD in .env file.\n"
            "Copy .env.example to .env and fill in your credentials."
        )
