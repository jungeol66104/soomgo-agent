"""Test script for authentication module."""

import asyncio
from loguru import logger
from src.scraper.auth import get_authenticated_browser, close_browser


async def main():
    """Test the authentication flow."""
    logger.info("=" * 60)
    logger.info("Testing Soomgo Authentication")
    logger.info("=" * 60)

    try:
        # Get authenticated browser
        browser, context = await get_authenticated_browser()

        # Create a test page to verify we're logged in
        page = await context.new_page()
        await page.goto("https://soomgo.com")
        await page.wait_for_timeout(3000)

        # Take a screenshot for verification
        await page.screenshot(path="logs/logged_in.png")
        logger.info("Screenshot saved to logs/logged_in.png")

        # Print current URL
        logger.info(f"Current URL: {page.url}")

        # Keep browser open for manual inspection if not headless
        logger.info("Browser is ready. Check the window to verify login status.")
        logger.info("Press Ctrl+C to close...")

        # Wait for user to inspect
        await page.wait_for_timeout(30000)

        await page.close()
        await close_browser(browser, context)

        logger.success("Authentication test completed successfully!")

    except Exception as e:
        logger.error(f"Authentication test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
