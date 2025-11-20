"""Authentication module for Soomgo login and session management."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from src import config


async def fresh_login(email: str, password: str, browser: Browser) -> BrowserContext:
    """
    Perform a fresh login to Soomgo.

    Args:
        email: Soomgo account email
        password: Soomgo account password
        browser: Playwright browser instance

    Returns:
        Authenticated browser context
    """
    logger.info("Starting fresh login to Soomgo...")

    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Navigate to Soomgo login page (use domcontentloaded for faster loading)
        logger.info("Navigating to Soomgo login page...")
        await page.goto(
            "https://soomgo.com/login?from=gnb&entry_point=signup_cta",
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Wait for the page to render (React needs time)
        await page.wait_for_timeout(3000)
        logger.info("Page loaded, looking for login form...")

        # Try multiple selectors for email field
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[placeholder*="이메일"]',
            'input[id*="email"]'
        ]

        email_filled = False
        for selector in email_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.fill(selector, email)
                logger.info(f"✓ Email filled using selector: {selector}")
                email_filled = True
                break
            except:
                continue

        if not email_filled:
            raise Exception("Could not find email input field")

        # Try multiple selectors for password field
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="비밀번호"]',
            'input[id*="password"]'
        ]

        password_filled = False
        for selector in password_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.fill(selector, password)
                logger.info(f"✓ Password filled using selector: {selector}")
                password_filled = True
                break
            except:
                continue

        if not password_filled:
            raise Exception("Could not find password input field")

        # Wait a bit before clicking
        await page.wait_for_timeout(1000)

        # Try multiple selectors for login button
        logger.info("Submitting login form...")
        button_selectors = [
            'button[type="submit"]',
            'button:has-text("로그인")',
            'button:has-text("로그인하기")',
            '[role="button"]:has-text("로그인")',
            'button.login-button',
            'button#login-button'
        ]

        button_clicked = False
        for selector in button_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                await page.click(selector)
                logger.info(f"✓ Login button clicked using selector: {selector}")
                button_clicked = True
                break
            except:
                continue

        if not button_clicked:
            raise Exception("Could not find login button")

        # Wait for navigation/response after login
        logger.info("Waiting for login to complete...")
        await page.wait_for_timeout(5000)

        # Verify login was successful
        current_url = page.url
        logger.info(f"Current URL after login: {current_url}")

        # Take screenshot for verification
        await page.screenshot(path="logs/after_login.png")

        # Check if we're still on the /login page (not just URL params containing "login")
        from urllib.parse import urlparse
        parsed_url = urlparse(current_url)

        if parsed_url.path.startswith("/login"):
            logger.error("Still on login page - login may have failed")
            await page.screenshot(path="logs/login_failed.png")
            raise Exception("Login failed - still on login page. Check logs/login_failed.png")

        logger.success(f"Login successful! Redirected to: {current_url}")
        return context

    except Exception as e:
        logger.error(f"Login failed: {e}")
        await page.screenshot(path="logs/login_error.png")
        await context.close()
        raise


async def save_session(context: BrowserContext, session_file: Path):
    """
    Save browser session (cookies + localStorage) to file.

    Args:
        context: Authenticated browser context
        session_file: Path to save session data
    """
    logger.info(f"Saving session to {session_file}...")
    await context.storage_state(path=str(session_file))
    logger.success("Session saved successfully!")


async def load_session(browser: Browser, session_file: Path) -> BrowserContext:
    """
    Load browser session from file.

    Args:
        browser: Playwright browser instance
        session_file: Path to saved session data

    Returns:
        Browser context with loaded session
    """
    logger.info(f"Loading session from {session_file}...")
    context = await browser.new_context(storage_state=str(session_file))
    logger.success("Session loaded successfully!")
    return context


async def validate_session(context: BrowserContext) -> bool:
    """
    Check if the loaded session is still valid.

    Args:
        context: Browser context to validate

    Returns:
        True if session is valid, False otherwise
    """
    logger.info("Validating session...")
    page = await context.new_page()

    try:
        # Navigate to a page that requires login (use domcontentloaded)
        await page.goto("https://soomgo.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Check if we're logged in (look for login button = not logged in)
        # Try multiple selectors for login button
        login_button_selectors = [
            'text="로그인"',
            'a:has-text("로그인")',
            'button:has-text("로그인")',
            '[href*="login"]'
        ]

        is_logged_out = False
        for selector in login_button_selectors:
            try:
                is_visible = await page.locator(selector).first.is_visible(timeout=3000)
                if is_visible:
                    is_logged_out = True
                    break
            except:
                continue

        if is_logged_out:
            logger.warning("Session expired - login button is visible")
            await page.close()
            return False

        logger.success("Session is valid!")
        await page.close()
        return True

    except Exception as e:
        logger.warning(f"Session validation failed: {e}")
        try:
            await page.close()
        except:
            pass
        return False


async def get_authenticated_browser() -> tuple[Browser, BrowserContext]:
    """
    Get an authenticated browser context, reusing session if valid or performing fresh login.

    This is the main entry point for authentication.

    Returns:
        Tuple of (browser, context) - both need to be closed when done
    """
    config.validate_config()

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=config.HEADLESS)

    # Try to load existing session
    if config.SESSION_FILE.exists():
        logger.info("Found existing session file...")
        try:
            context = await load_session(browser, config.SESSION_FILE)

            # Validate session
            if await validate_session(context):
                logger.success("Using existing session - no login needed!")
                return browser, context
            else:
                logger.warning("Session expired, performing fresh login...")
                await context.close()
        except Exception as e:
            logger.warning(f"Failed to load session: {e}")

    # No valid session - perform fresh login
    context = await fresh_login(
        config.SOOMGO_EMAIL,
        config.SOOMGO_PASSWORD,
        browser
    )

    # Save session for future use
    await save_session(context, config.SESSION_FILE)

    return browser, context


async def close_browser(browser: Browser, context: BrowserContext):
    """
    Properly close browser and context.

    Args:
        browser: Browser instance to close
        context: Context instance to close
    """
    logger.info("Closing browser...")
    await context.close()
    await browser.close()
    logger.info("Browser closed.")
