"""Run message scraping with skip-existing and 3 workers."""

import asyncio
from src.scraper.auth import get_authenticated_browser
from src.scraper.chat_message_scraper import scrape_chat_messages


async def main():
    """Run full message scraping with skip-existing mode and 3 workers."""
    browser, context = await get_authenticated_browser()

    try:
        print("Starting message scraping (FULL RUN - 3 workers, skip-existing enabled)...")
        run_dir = await scrape_chat_messages(
            context,
            date_filter="all",
            dry_run=False,  # Full production run
            workers=3,
            skip_existing=True
        )
        print(f"\nScraping completed! Check results at: {run_dir}")

    finally:
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
