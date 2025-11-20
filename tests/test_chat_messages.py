"""Test script for chat message scraping."""

import asyncio
from src.scraper.auth import get_authenticated_browser
from src.scraper.chat_message_scraper import scrape_chat_messages


async def main():
    """Test message scraping with dry run."""
    import sys

    # Check for --workers flag
    workers = 1  # Default
    if "--workers" in sys.argv:
        try:
            workers_index = sys.argv.index("--workers")
            workers = int(sys.argv[workers_index + 1])
        except (IndexError, ValueError):
            print("Invalid --workers value, using default (1)")

    # Check for --skip-existing flag
    skip_existing = "--skip-existing" in sys.argv

    # Get authenticated browser
    browser, context = await get_authenticated_browser()

    try:
        # Run message scraper in dry run mode (only 3 chats)
        mode_str = f"DRY RUN - 3 chats, {workers} worker(s)"
        if skip_existing:
            mode_str += ", skip-existing enabled"
        print(f"Starting message scraping ({mode_str})...")
        run_dir = await scrape_chat_messages(
            context,
            date_filter="all",  # or "30days"
            dry_run=True,
            dry_run_limit=3,
            workers=workers,
            skip_existing=skip_existing
        )
        print(f"\nDry run completed! Check results at: {run_dir}")

    finally:
        # Clean up
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
