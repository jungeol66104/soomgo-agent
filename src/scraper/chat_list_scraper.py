"""Chat list scraper using browser API interception."""

import asyncio
from pathlib import Path
from typing import List, Dict, Any
from playwright.async_api import Page, BrowserContext
from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from src.utils import (
    RunLogger,
    ChatListTracker,
    save_to_jsonl,
    humanized_scroll,
    move_mouse_randomly,
    wait_for_network_idle,
    extract_service_titles,
    get_date_range,
    HumanizationTracker,
    random_session_break,
    randomize_viewport,
    apply_rate_limit,
    exponential_backoff
)
from src.scraper.data_quality import generate_quality_report
from src.scraper.central_db import CentralChatDatabase
from src.models import ChatItem


class ChatListScraper:
    """Scrapes chat list from Soomgo using API interception."""

    def __init__(self, run_logger: RunLogger, dry_run: bool = False, dry_run_limit: int = 50, date_filter: str = "all"):
        self.run_logger = run_logger
        self.tracker = ChatListTracker()
        self.api_responses: List[Dict[str, Any]] = []
        self.api_call_count = 0
        self.scroll_count = 0
        self.checkpoint_interval = 50  # Save checkpoint every 50 chats
        self.has_more_chats = True  # Flag to track if more chats available
        self.last_activity_time = None  # Track last API response time
        self.progress = None  # Progress bar instance
        self.humanization_tracker = HumanizationTracker()  # Track humanization stats
        self.dry_run = dry_run  # Dry run mode
        self.dry_run_limit = dry_run_limit  # Stop after N chats in dry run
        self.backoff_count = 0  # Track exponential backoff events
        self.viewport_change_count = 0  # Track viewport changes
        self.date_filter = date_filter  # Date filter: "all" or "30days"

        # Calculate cutoff date for 30days filter
        self.date_cutoff = None
        if self.date_filter == "30days":
            from datetime import datetime, timedelta
            self.date_cutoff = datetime.now() - timedelta(days=30)
            logger.info(f"Date filter: 30days (cutoff: {self.date_cutoff.strftime('%Y-%m-%d')})")

    async def intercept_api_response(self, response):
        """Handler for intercepted API responses."""
        try:
            # Check if this is the chat list API
            if "api.soomgo.com/api/v2.4/chats" in response.url and response.status == 200:
                data = await response.json()

                # Update last activity time
                import time
                from datetime import datetime
                self.last_activity_time = time.time()

                # Track first/last API call timestamps (only for ChatListScrapingRunMetadata)
                now = datetime.now()
                if hasattr(self.run_logger.metadata, 'first_api_call_at'):
                    if self.run_logger.metadata.first_api_call_at is None:
                        self.run_logger.metadata.first_api_call_at = now
                    self.run_logger.metadata.last_api_call_at = now

                # Save raw response
                self.api_call_count += 1
                if not self.dry_run:  # Don't save in dry run mode
                    self.run_logger.save_api_response(data, self.api_call_count)

                # Add to responses list
                self.api_responses.append(data)

                # Check if there are more chats (API signals via "next" field)
                if data.get("next") is None or not data.get("results"):
                    self.has_more_chats = False
                    logger.success("API indicates no more chats available (next=null or empty results)")

                # Process chats
                new_count = self.tracker.add_chats_from_response(data)
                total_chats = len(self.tracker.all_chats)

                logger.info(f"API Call #{self.api_call_count}: +{new_count} new chats (Total: {total_chats})")

                # Check date filter: stop if we've reached chats older than cutoff
                if self.date_cutoff and data.get("results"):
                    from datetime import datetime
                    # Check the oldest chat in this batch (results are in reverse chronological order)
                    for chat_data in reversed(data.get("results", [])):
                        try:
                            updated_at_str = chat_data.get("updated_at", "")
                            if updated_at_str:
                                # Parse ISO format datetime
                                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                                if updated_at < self.date_cutoff:
                                    self.has_more_chats = False
                                    logger.success(f"Reached date cutoff ({self.date_cutoff.strftime('%Y-%m-%d')}) - stopping")
                                    break
                        except Exception as e:
                            logger.debug(f"Error parsing date for chat: {e}")
                            continue

                # Update progress bar
                if self.progress:
                    self.progress.update(
                        self.progress_task,
                        completed=total_chats,
                        description=f"[cyan]Scraping chats... ({total_chats} found)"
                    )

                # Update metadata
                self.run_logger.metadata.total_items_found += len(data.get("results", []))
                self.run_logger.metadata.total_items_processed = total_chats
                self.run_logger.metadata.total_duplicates_filtered = self.tracker.duplicate_count

                # Checkpoint
                if total_chats % self.checkpoint_interval == 0:
                    checkpoint_file = self.run_logger.run_dir / "checkpoint.json"
                    self.tracker.save_checkpoint(checkpoint_file)

        except Exception as e:
            logger.error(f"Error processing API response: {e}")
            self.run_logger.log_error(e, "API response processing")

    async def wait_for_new_api_call(self, timeout: int = 10000) -> bool:
        """
        Wait for a new API call to be intercepted.

        Returns:
            True if new call detected, False if timeout
        """
        start_count = self.api_call_count
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout / 1000:
            if self.api_call_count > start_count:
                return True
            await asyncio.sleep(0.5)

        return False

    async def scroll_until_complete(self, page: Page, max_scrolls: int = 10000):
        """
        Scroll the page until API returns next=null (no more chats).

        ONLY stops when:
        - API returns next=null (definitive end)
        - Dry run limit reached
        - Max scrolls safety limit (10000 - effectively unlimited for historical data)

        Args:
            page: Playwright page object
            max_scrolls: Safety limit (default: 10000)
        """
        logger.info("Starting scroll to load all chats...")
        logger.info("Will continue until API returns next=null")

        import time
        start_time = time.time()
        self.last_activity_time = start_time

        for scroll_num in range(max_scrolls):
            # Check dry run limit
            if self.dry_run and len(self.tracker.all_chats) >= self.dry_run_limit:
                logger.success(f"[DRY RUN] Reached limit of {self.dry_run_limit} chats")
                break

            # PRIMARY STOP CONDITION: Check if API says no more chats (next=null)
            if not self.has_more_chats:
                logger.success("✓ API returned next=null - All chats loaded!")
                break

            self.scroll_count += 1

            # Track chat count before scroll
            chats_before = len(self.tracker.all_chats)

            # Viewport randomization (every 10 scrolls)
            if self.scroll_count % 10 == 0:
                await randomize_viewport(page)
                self.viewport_change_count += 1

            # Humanized scroll (scrolls observer into view to trigger API)
            logger.debug(f"Scroll #{self.scroll_count} (Total chats: {len(self.tracker.all_chats)})")
            await humanized_scroll(page, self.humanization_tracker)

            # Occasionally move mouse
            await move_mouse_randomly(page, self.humanization_tracker)

            # Random session break (5% chance per scroll)
            await random_session_break(page, self.humanization_tracker)

            # Rate limiting (2-5 second delay between scrolls)
            await apply_rate_limit(min_delay=2.0, max_delay=5.0)

            # Wait for the observer to trigger API call
            # Give extra time for Intersection Observer to fire
            await asyncio.sleep(2)  # Let observer detect visibility
            new_call = await self.wait_for_new_api_call(timeout=10000)  # 10s wait for API

            # Log progress
            chats_after = len(self.tracker.all_chats)
            if chats_after > chats_before:
                logger.info(f"✓ Loaded {chats_after - chats_before} new chats (Total: {chats_after})")
            else:
                logger.debug(f"No new chats this scroll (waiting for next=null from API)")

        if scroll_num >= max_scrolls - 1:
            self.run_logger.log_warning(f"⚠ Reached max scroll safety limit ({max_scrolls})")

    async def scrape(self, page: Page) -> List[Dict[str, Any]]:
        """
        Main scraping method.

        Args:
            page: Playwright page object (already on chat list page)

        Returns:
            List of all scraped chats
        """
        try:
            logger.info("Starting chat list scraping...")

            # Set up API interception
            page.on("response", self.intercept_api_response)

            # Navigate to chat list page
            logger.info("Navigating to /pro/chats...")
            await page.goto("https://soomgo.com/pro/chats", wait_until="domcontentloaded", timeout=60000)

            # Wait for initial load
            await asyncio.sleep(3)
            await wait_for_network_idle(page)

            # Take initial screenshot
            await self.run_logger.save_screenshot(page, "initial_state")

            # Scroll to load all chats with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[cyan]{task.completed} chats"),
                TimeElapsedColumn(),
            ) as progress:
                self.progress = progress
                self.progress_task = progress.add_task(
                    "[cyan]Scraping chats...",
                    total=None  # Unknown total
                )

                await self.scroll_until_complete(page)

                # Mark as complete
                progress.update(self.progress_task, description="[green]✓ Scraping complete!")

            # Take final screenshot
            await self.run_logger.save_screenshot(page, "final_state")

            # Update metadata
            self.run_logger.metadata.scroll_iterations = self.scroll_count
            self.run_logger.metadata.api_calls_intercepted = self.api_call_count
            self.run_logger.metadata.viewport_changes = self.viewport_change_count
            self.run_logger.metadata.backoff_events = self.backoff_count

            # Save humanization stats
            self.run_logger.metadata.humanization_stats.reading_pauses = self.humanization_tracker.reading_pauses
            self.run_logger.metadata.humanization_stats.scroll_ups = self.humanization_tracker.scroll_ups
            self.run_logger.metadata.humanization_stats.mouse_movements = self.humanization_tracker.mouse_movements
            self.run_logger.metadata.humanization_stats.session_breaks = self.humanization_tracker.session_breaks
            self.run_logger.metadata.humanization_stats.total_wait_time_seconds = self.humanization_tracker.total_wait_time

            # Calculate efficiency metrics
            total_chats = len(self.tracker.all_chats)
            if self.api_call_count > 0:
                self.run_logger.metadata.efficiency_metrics.chats_per_api_call = total_chats / self.api_call_count
            if self.scroll_count > 0:
                self.run_logger.metadata.efficiency_metrics.chats_per_scroll = total_chats / self.scroll_count

            # Calculate rates (per minute)
            if (hasattr(self.run_logger.metadata, 'first_api_call_at') and
                hasattr(self.run_logger.metadata, 'last_api_call_at') and
                self.run_logger.metadata.first_api_call_at and
                self.run_logger.metadata.last_api_call_at):
                duration_minutes = (self.run_logger.metadata.last_api_call_at - self.run_logger.metadata.first_api_call_at).total_seconds() / 60
                if duration_minutes > 0:
                    self.run_logger.metadata.efficiency_metrics.api_calls_per_minute = self.api_call_count / duration_minutes
                    self.run_logger.metadata.efficiency_metrics.scrolls_per_minute = self.scroll_count / duration_minutes

            # Extract statistics
            if self.tracker.all_chats:
                services = extract_service_titles(self.tracker.all_chats)
                oldest, newest = get_date_range(self.tracker.all_chats)

                self.run_logger.metadata.unique_services = services
                self.run_logger.metadata.oldest_chat_date = oldest
                self.run_logger.metadata.newest_chat_date = newest

                logger.info(f"Services found: {', '.join(services)}")
                logger.info(f"Date range: {oldest} to {newest}")

            # Log efficiency stats
            em = self.run_logger.metadata.efficiency_metrics
            chats_per_api = f"{em.chats_per_api_call:.2f}" if em.chats_per_api_call else "N/A"
            chats_per_scroll = f"{em.chats_per_scroll:.2f}" if em.chats_per_scroll else "N/A"
            logger.info(f"Efficiency: {chats_per_api} chats/API call, {chats_per_scroll} chats/scroll")
            logger.info(f"Humanization: {self.humanization_tracker.reading_pauses} pauses, "
                       f"{self.humanization_tracker.scroll_ups} scroll-ups, "
                       f"{self.humanization_tracker.mouse_movements} mouse moves, "
                       f"{self.humanization_tracker.session_breaks} breaks")

            if self.dry_run:
                logger.success(f"[DRY RUN] Preview complete! Found {len(self.tracker.all_chats)} chats")
            else:
                logger.success(f"Scraping complete! Total chats: {len(self.tracker.all_chats)}")

            return self.tracker.all_chats

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            self.run_logger.log_error(e, "Main scraping loop")
            raise


async def scrape_chat_list(context: BrowserContext, dry_run: bool = False, dry_run_limit: int = 50, date_filter: str = "all") -> Path:
    """
    High-level function to scrape the entire chat list.

    Args:
        context: Authenticated browser context
        dry_run: If True, only preview first N chats without saving full output
        dry_run_limit: Number of chats to preview in dry run mode
        date_filter: "all" or "30days" - stop scraping when reaching chats older than cutoff

    Returns:
        Path to the run directory containing results
    """
    # Initialize run logger
    config = {
        "checkpoint_interval": 50,
        "max_scrolls": 10000,
        "scroll_wait_time": 2000,
        "dry_run": dry_run,
        "dry_run_limit": dry_run_limit if dry_run else None,
        "date_filter": date_filter
    }
    run_type = "chat_list_dryrun" if dry_run else "chat_list"
    run_logger = RunLogger(run_type, config)

    try:
        # Create scraper
        scraper = ChatListScraper(run_logger, dry_run=dry_run, dry_run_limit=dry_run_limit, date_filter=date_filter)

        # Create new page
        page = await context.new_page()

        # Scrape
        chats = await scraper.scrape(page)

        # Generate data quality report
        logger.info("Generating data quality report...")
        quality_report = generate_quality_report(chats)

        # Save quality report
        import json
        quality_report_file = run_logger.run_dir / "data_quality_report.json"
        with open(quality_report_file, 'w', encoding='utf-8') as f:
            json.dump(quality_report.dict(), f, indent=2, ensure_ascii=False, default=str)
        run_logger.metadata.output_files.append(str(quality_report_file))
        logger.success(f"Quality Score: {quality_report.quality_score}/100 ({quality_report.quality_grade})")

        # Update central database (skip in dry run mode)
        if not dry_run:
            logger.info("Updating central database...")
            central_db = CentralChatDatabase()

            # Convert dict chats to ChatItem objects if needed
            chat_items = []
            for chat in chats:
                if isinstance(chat, dict):
                    chat_items.append(ChatItem(**chat))
                else:
                    chat_items.append(chat)

            # Load existing database
            existing_chats = central_db.load()

            # Merge and update
            merged_chats, new_count, updated_count = central_db.merge_and_update(
                existing=existing_chats,
                new_chats=chat_items
            )

            # Save back to central database
            central_db.save(merged_chats)

            logger.success(f"Central database updated: {new_count} new, {updated_count} updated, {len(merged_chats)} total")

        # Save results (skip full output in dry run mode)
        if not dry_run:
            output_file = run_logger.run_dir / "chat_list.jsonl"
            save_to_jsonl(chats, output_file)
            run_logger.metadata.output_files.append(str(output_file))

            # Also save as regular JSON for easy viewing
            json_file = run_logger.run_dir / "chat_list.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(chats, f, indent=2, ensure_ascii=False)
            run_logger.metadata.output_files.append(str(json_file))
        else:
            # In dry run, save a preview sample
            preview_file = run_logger.run_dir / "preview_sample.json"
            sample = chats[:min(10, len(chats))]  # First 10 chats as preview
            with open(preview_file, 'w', encoding='utf-8') as f:
                json.dump(sample, f, indent=2, ensure_ascii=False)
            run_logger.metadata.output_files.append(str(preview_file))
            logger.info(f"Preview sample (first {len(sample)} chats) saved")

        # Close page
        await page.close()

        # Finalize
        status = "completed" if not dry_run else "dry_run_completed"
        run_dir = run_logger.finalize(status)

        if dry_run:
            logger.success(f"[DRY RUN] Preview completed: {run_dir}")
            logger.success(f"Total chats found: {len(chats)} (stopped at limit)")
        else:
            logger.success(f"Results saved to: {run_dir}")
            logger.success(f"Total chats scraped: {len(chats)}")

        return run_dir

    except Exception as e:
        logger.error(f"Chat list scraping failed: {e}")
        run_logger.finalize("failed")
        raise
