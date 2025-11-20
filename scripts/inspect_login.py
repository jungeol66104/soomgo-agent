"""Helper script to inspect Soomgo login page and find correct selectors."""

import asyncio
from playwright.async_api import async_playwright


async def main():
    """Open Soomgo login page for manual inspection."""
    async with async_playwright() as p:
        # Launch browser in headed mode with slow motion
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=1000  # Slow down by 1 second to see actions
        )

        context = await browser.new_context()
        page = await context.new_page()

        print("=" * 60)
        print("Opening Soomgo login page...")
        print("=" * 60)

        # Navigate to login page
        await page.goto("https://soomgo.com/login?from=gnb&entry_point=signup_cta")

        # Wait for page to load
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(3000)

        print("\n📋 Finding login form elements...")
        print("-" * 60)

        # Try to find email input
        try:
            email_input = await page.query_selector('input[type="email"]')
            if email_input:
                email_id = await email_input.get_attribute("id")
                email_name = await email_input.get_attribute("name")
                email_placeholder = await email_input.get_attribute("placeholder")
                print(f"✓ Email input found:")
                print(f"  - id: {email_id}")
                print(f"  - name: {email_name}")
                print(f"  - placeholder: {email_placeholder}")
            else:
                print("✗ Email input not found with type='email'")
        except Exception as e:
            print(f"✗ Error finding email input: {e}")

        # Try to find password input
        try:
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                password_id = await password_input.get_attribute("id")
                password_name = await password_input.get_attribute("name")
                password_placeholder = await password_input.get_attribute("placeholder")
                print(f"\n✓ Password input found:")
                print(f"  - id: {password_id}")
                print(f"  - name: {password_name}")
                print(f"  - placeholder: {password_placeholder}")
            else:
                print("\n✗ Password input not found with type='password'")
        except Exception as e:
            print(f"\n✗ Error finding password input: {e}")

        # Try to find login button
        try:
            # Try multiple selectors for button
            button_selectors = [
                'button[type="submit"]',
                'button:has-text("로그인")',
                'button:has-text("로그인하기")',
                '[role="button"]:has-text("로그인")'
            ]

            button_found = False
            for selector in button_selectors:
                button = await page.query_selector(selector)
                if button:
                    button_text = await button.text_content()
                    button_type = await button.get_attribute("type")
                    print(f"\n✓ Login button found with selector: {selector}")
                    print(f"  - text: {button_text}")
                    print(f"  - type: {button_type}")
                    button_found = True
                    break

            if not button_found:
                print("\n✗ Login button not found with any selector")
        except Exception as e:
            print(f"\n✗ Error finding login button: {e}")

        print("\n" + "=" * 60)
        print("Keeping browser open for 60 seconds...")
        print("You can manually inspect elements in DevTools")
        print("Press Ctrl+C to close early")
        print("=" * 60)

        # Keep browser open
        try:
            await page.wait_for_timeout(60000)
        except KeyboardInterrupt:
            print("\nClosing browser...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
