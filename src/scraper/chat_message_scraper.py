"""Chat message scraper using browser API interception."""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, BrowserContext
from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from src.utils import (
    RunLogger,
    save_to_jsonl,
    wait_for_network_idle,
    HumanizationTracker,
    apply_rate_limit,
    exponential_backoff
)
from src.models import (
    MessageItem,
    MessageListResponse,
    ChatItem,
    MessageScrapingRunMetadata,
    ChatScrapingStatus
)
from src.scraper.message_central_db import MessageCentralDB
from src.scraper.central_db import CentralChatDatabase
from src.scraper.data_quality import generate_quality_report


class MessageTracker:
    """Tracks messages collected for a single chat."""

    def __init__(self):
        self.all_messages: List[MessageItem] = []
        self.message_ids: set = set()
        self.duplicate_count = 0

    def add_messages_from_response(self, response_data: Dict[str, Any]) -> int:
        """Add messages from API response, deduplicating by ID.

        Returns:
            Number of new messages added
        """
        try:
            response = MessageListResponse(**response_data)
            new_count = 0

            for message in response.results:
                if message.id not in self.message_ids:
                    self.all_messages.append(message)
                    self.message_ids.add(message.id)
                    new_count += 1
                else:
                    self.duplicate_count += 1

            return new_count

        except Exception as e:
            logger.error(f"Error processing message response: {e}")
            return 0


class ChatMessageScraper:
    """Scrapes messages for a single chat using API interception."""

    def __init__(self, chat_id: int):
        """Initialize scraper for a specific chat.

        Args:
            chat_id: ID of the chat to scrape
        """
        self.chat_id = chat_id
        self.tracker = MessageTracker()
        self.api_responses: List[Dict[str, Any]] = []
        self.api_call_count = 0
        self.scroll_count = 0
        self.has_more_messages = True
        self.humanization_tracker = HumanizationTracker()
        self.api_intercept_errors = 0  # Track failed API response reads

    async def intercept_api_response(self, response):
        """Handler for intercepted API responses."""
        try:
            # Check if this is the messages API for our chat
            expected_url = f"api.soomgo.com/api/v2.2/chats/{self.chat_id}/messages"
            if expected_url in response.url and response.status == 200:
                # Try to read response body with error tracking
                try:
                    data = await response.json()
                except Exception as json_error:
                    # Protocol error: response body not available
                    self.api_intercept_errors += 1
                    logger.warning(f"Chat {self.chat_id}: API intercept error #{self.api_intercept_errors} - {json_error}")
                    return

                # Save response
                self.api_call_count += 1
                self.api_responses.append(data)

                # Check if there are more messages
                if data.get("next") is None:
                    self.has_more_messages = False
                    logger.success(f"Chat {self.chat_id}: API indicates no more messages (next=null)")

                # Process messages
                new_count = self.tracker.add_messages_from_response(data)
                total_messages = len(self.tracker.all_messages)

                logger.info(f"Chat {self.chat_id} API Call #{self.api_call_count}: +{new_count} new messages (Total: {total_messages})")

        except Exception as e:
            logger.error(f"Error processing API response for chat {self.chat_id}: {e}")

    async def scroll_to_load_messages(self, page: Page) -> None:
        """Scroll up to load older messages.

        Args:
            page: Playwright page object
        """
        # Scroll to top of message container to load older messages
        await page.evaluate("""
            () => {
                const container = document.querySelector('.chat-messages');
                if (container) {
                    container.scrollTop = 0;
                }
            }
        """)

        # Small humanization delay
        await asyncio.sleep(1.5 + (asyncio.get_event_loop().time() % 1.5))
        self.humanization_tracker.total_wait_time += 1.5

    async def wait_for_new_api_call(self, timeout: int = 8000) -> bool:
        """Wait for a new API call to be intercepted.

        Args:
            timeout: Timeout in milliseconds

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

    async def scroll_until_complete(self, page: Page, max_scrolls: int = 300):
        """Scroll the chat to load all messages until API returns next=null.

        Args:
            page: Playwright page object
            max_scrolls: Safety limit for scrolls
        """
        logger.info(f"Chat {self.chat_id}: Starting scroll to load all messages...")

        for scroll_num in range(max_scrolls):
            # PRIMARY STOP CONDITION: Check if API says no more messages
            if not self.has_more_messages:
                logger.success(f"Chat {self.chat_id}: ✓ All messages loaded (next=null)")
                break

            self.scroll_count += 1

            # Track messages before scroll
            messages_before = len(self.tracker.all_messages)

            # Scroll up to load older messages
            logger.debug(f"Chat {self.chat_id} Scroll #{self.scroll_count}")
            await self.scroll_to_load_messages(page)

            # Wait for API response
            await asyncio.sleep(1)  # Let scroll trigger API call
            new_call = await self.wait_for_new_api_call(timeout=8000)

            # Log progress
            messages_after = len(self.tracker.all_messages)
            if messages_after > messages_before:
                logger.info(f"Chat {self.chat_id}: ✓ Loaded {messages_after - messages_before} new messages (Total: {messages_after})")

            # Faster humanization for messages (1-3 second delay)
            delay = 1.0 + (asyncio.get_event_loop().time() % 2.0)
            await asyncio.sleep(delay)
            self.humanization_tracker.total_wait_time += delay

        if scroll_num >= max_scrolls - 1:
            logger.warning(f"Chat {self.chat_id}: ⚠ Reached max scroll limit ({max_scrolls})")

    async def scrape(self, page: Page) -> List[MessageItem]:
        """Scrape all messages for this chat.

        Args:
            page: Playwright page object

        Returns:
            List of all messages
        """
        try:
            logger.info(f"Starting message scraping for chat {self.chat_id}...")

            # Set up API interception
            page.on("response", self.intercept_api_response)

            # Navigate to chat page
            chat_url = f"https://soomgo.com/pro/chats/{self.chat_id}?from=chatroom"
            logger.info(f"Navigating to {chat_url}...")
            await page.goto(chat_url, wait_until="domcontentloaded", timeout=60000)

            # Wait for initial load
            await asyncio.sleep(3)
            await wait_for_network_idle(page)

            # Scroll to load all messages
            await self.scroll_until_complete(page)

            logger.success(f"Chat {self.chat_id}: Scraping complete! Total messages: {len(self.tracker.all_messages)}")

            return self.tracker.all_messages

        except Exception as e:
            logger.error(f"Error scraping chat {self.chat_id}: {e}")
            raise


async def scrape_worker(
    worker_id: int,
    assigned_chats: List[ChatItem],
    page: Page,
    message_db: MessageCentralDB,
    dry_run: bool,
    progress,
    progress_task
) -> tuple[List[MessageItem], List[ChatScrapingStatus], HumanizationTracker]:
    """Worker function to scrape assigned chats.

    Args:
        worker_id: Worker identifier
        assigned_chats: List of chats assigned to this worker
        page: Playwright page for this worker
        message_db: Central message database
        dry_run: Whether in dry run mode
        progress: Progress bar instance
        progress_task: Progress task ID

    Returns:
        Tuple of (messages, statuses, humanization_tracker)
    """
    worker_messages = []
    worker_statuses = []
    worker_humanization = HumanizationTracker()

    for idx, chat in enumerate(assigned_chats, 1):
        chat_start_time = time.time()

        try:
            logger.info(f"Worker {worker_id}: Chat {idx}/{len(assigned_chats)} - {chat.id} ({chat.service.title})")

            # Create scraper for this chat
            scraper = ChatMessageScraper(chat.id)

            # Scrape messages
            messages = await scraper.scrape(page)

            # Validate results before saving
            is_suspicious = False
            failure_reason = None

            if len(messages) == 0 and scraper.scroll_count > 0:
                is_suspicious = True
                failure_reason = f"0 messages after {scraper.scroll_count} scrolls"
            elif scraper.api_intercept_errors > 0:
                is_suspicious = True
                failure_reason = f"{scraper.api_intercept_errors} API intercept errors"

            # Update message central DB only if results are valid (skip in dry run)
            if not dry_run:
                if is_suspicious:
                    logger.error(f"Worker {worker_id}: Chat {chat.id} - FAILED validation: {failure_reason}. NOT saving file.")
                else:
                    existing_messages = message_db.load_chat_messages(chat.id)
                    merged, new_count, updated_count = message_db.merge_and_update(
                        chat.id,
                        existing_messages,
                        messages
                    )
                    message_db.save_chat_messages(chat.id, merged)
                    logger.success(f"Worker {worker_id}: Chat {chat.id} - Updated DB ({new_count} new, {updated_count} updated)")

            # Collect messages (even if suspicious, for reporting)
            worker_messages.extend(messages)

            # Track status
            chat_duration = time.time() - chat_start_time
            status = ChatScrapingStatus(
                chat_id=chat.id,
                status="failed" if is_suspicious else "success",
                message_count=len(messages),
                api_calls=scraper.api_call_count,
                scroll_iterations=scraper.scroll_count,
                duration_seconds=chat_duration,
                error=failure_reason if is_suspicious else None
            )
            worker_statuses.append(status)

            # Aggregate humanization stats
            worker_humanization.total_wait_time += scraper.humanization_tracker.total_wait_time

            # Update progress
            if progress:
                progress.update(progress_task, advance=1)

            # Delay between chats (3-7 seconds, random)
            if idx < len(assigned_chats):  # Don't delay after last chat
                delay = 3.0 + (time.time() % 4.0)
                logger.debug(f"Worker {worker_id}: Waiting {delay:.1f}s before next chat...")
                await asyncio.sleep(delay)
                worker_humanization.total_wait_time += delay

                # Long break every 20 chats
                if idx % 20 == 0:
                    break_time = 15 + (time.time() % 15)
                    logger.info(f"Worker {worker_id}: Taking session break ({break_time:.1f}s)...")
                    await asyncio.sleep(break_time)
                    worker_humanization.session_breaks += 1
                    worker_humanization.total_wait_time += break_time

        except Exception as e:
            logger.error(f"Worker {worker_id}: Failed to scrape chat {chat.id}: {e}")

            # Track failure
            chat_duration = time.time() - chat_start_time
            status = ChatScrapingStatus(
                chat_id=chat.id,
                status="failed",
                message_count=0,
                error=str(e),
                duration_seconds=chat_duration
            )
            worker_statuses.append(status)

            # Update progress even on failure
            if progress:
                progress.update(progress_task, advance=1)

    logger.success(f"Worker {worker_id}: Completed {len(assigned_chats)} chats")
    return worker_messages, worker_statuses, worker_humanization


def filter_chats_by_date(chats: List[ChatItem], filter_type: str) -> List[ChatItem]:
    """Filter chats by date.

    Args:
        chats: List of chats
        filter_type: "all" or "30days"

    Returns:
        Filtered list of chats
    """
    if filter_type == "all":
        return chats

    if filter_type == "30days":
        cutoff = datetime.now() - timedelta(days=30)
        filtered = []
        for chat in chats:
            try:
                # Parse updated_at date
                updated_at = datetime.fromisoformat(chat.updated_at.replace('Z', '+00:00'))
                if updated_at > cutoff:
                    filtered.append(chat)
            except Exception as e:
                logger.warning(f"Error parsing date for chat {chat.id}: {e}")
                # Include chat if we can't parse date (safer)
                filtered.append(chat)

        logger.info(f"Date filter '{filter_type}': {len(filtered)}/{len(chats)} chats")
        return filtered

    logger.warning(f"Unknown filter type: {filter_type}, returning all chats")
    return chats


async def scrape_chat_messages(
    context: BrowserContext,
    date_filter: str = "all",
    chat_limit: Optional[int] = None,
    dry_run: bool = False,
    dry_run_limit: int = 3,
    workers: int = 1,
    skip_existing: bool = False
) -> Path:
    """High-level function to scrape messages for multiple chats.

    Args:
        context: Authenticated browser context
        date_filter: "all" or "30days"
        chat_limit: Optional limit on number of chats to process
        dry_run: If True, only scrape a few chats for testing
        dry_run_limit: Number of chats to scrape in dry run mode
        workers: Number of concurrent workers (1=sequential, 2-3=parallel)
        skip_existing: If True, skip chats that already have message files

    Returns:
        Path to the run directory containing results
    """
    # Initialize run logger
    config = {
        "date_filter": date_filter,
        "chat_limit": chat_limit if not dry_run else dry_run_limit,
        "dry_run": dry_run,
        "workers": workers,
        "skip_existing": skip_existing
    }
    run_type = "messages_dryrun" if dry_run else "messages"
    run_logger = RunLogger(run_type, config)
    run_logger.metadata = MessageScrapingRunMetadata(
        run_id=run_logger.run_id,
        run_type=run_type,
        started_at=datetime.now(),
        status="in_progress",
        config=config,
        date_filter=date_filter,
        chat_limit=chat_limit
    )

    try:
        # Load chat list from central database
        logger.info("Loading chat list from central database...")
        chat_db = CentralChatDatabase()
        all_chats_dict = chat_db.load()

        if not all_chats_dict:
            logger.error("No chats found in central database. Run chat list scraper first!")
            raise ValueError("No chats in central database")

        all_chats = list(all_chats_dict.values())
        logger.info(f"Loaded {len(all_chats)} chats from central database")

        # Apply date filter
        filtered_chats = filter_chats_by_date(all_chats, date_filter)

        # Initialize message central DB early for skip-existing check
        message_db = MessageCentralDB()

        # Filter out existing chats if skip_existing is enabled
        if skip_existing and not dry_run:
            chats_before_skip = len(filtered_chats)
            filtered_chats = [
                chat for chat in filtered_chats
                if not message_db.chat_exists(chat.id)
            ]
            skipped_count = chats_before_skip - len(filtered_chats)
            logger.info(f"Skipped {skipped_count} existing chats (skip_existing mode)")

        # Apply limit (dry run or user-specified)
        if dry_run:
            chats_to_scrape = filtered_chats[:dry_run_limit]
        elif chat_limit:
            chats_to_scrape = filtered_chats[:chat_limit]
        else:
            chats_to_scrape = filtered_chats

        logger.info(f"Will scrape {len(chats_to_scrape)} chats with {workers} worker(s)")

        # Initialize tracking
        all_run_messages = []
        chat_statuses = []
        humanization_tracker = HumanizationTracker()

        # Create pages for workers
        pages = [await context.new_page() for _ in range(workers)]

        # Pre-assign chats to workers (round-robin distribution)
        worker_assignments = [[] for _ in range(workers)]
        for idx, chat in enumerate(chats_to_scrape):
            worker_id = idx % workers
            worker_assignments[worker_id].append(chat)

        # Log assignment distribution
        for worker_id, assigned in enumerate(worker_assignments):
            logger.info(f"Worker {worker_id}: Assigned {len(assigned)} chats")

        # Scrape with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total} chats"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task(
                f"[cyan]Scraping with {workers} worker(s)...",
                total=len(chats_to_scrape)
            )

            # Start all workers concurrently
            worker_tasks = [
                scrape_worker(
                    worker_id=i,
                    assigned_chats=worker_assignments[i],
                    page=pages[i],
                    message_db=message_db,
                    dry_run=dry_run,
                    progress=progress,
                    progress_task=task
                )
                for i in range(workers)
            ]

            # Wait for all workers to complete
            worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)

            # Aggregate results from all workers
            for worker_id, result in enumerate(worker_results):
                if isinstance(result, Exception):
                    logger.error(f"Worker {worker_id} failed with exception: {result}")
                    continue

                worker_messages, worker_statuses, worker_humanization = result

                # Merge results
                all_run_messages.extend(worker_messages)
                chat_statuses.extend(worker_statuses)
                humanization_tracker.total_wait_time += worker_humanization.total_wait_time
                humanization_tracker.session_breaks += worker_humanization.session_breaks

        # Close all pages
        for page in pages:
            await page.close()

        # Update metadata from aggregated results
        for status in chat_statuses:
            run_logger.metadata.chats_attempted += 1
            if status.status == "success":
                run_logger.metadata.chats_succeeded += 1
                run_logger.metadata.total_messages_scraped += status.message_count
            elif status.status == "failed":
                run_logger.metadata.chats_failed += 1

        # Save chat statuses
        run_logger.metadata.chat_statuses = chat_statuses
        run_logger.metadata.humanization_stats.total_wait_time_seconds = humanization_tracker.total_wait_time
        run_logger.metadata.humanization_stats.session_breaks = humanization_tracker.session_breaks

        # Generate quality report (on all messages from this run)
        logger.info("Generating data quality report...")
        # Convert MessageItem to dict for quality analysis
        messages_as_dicts = [msg.model_dump() for msg in all_run_messages]
        quality_report = generate_quality_report(messages_as_dicts)

        quality_report_file = run_logger.run_dir / "data_quality_report.json"
        with open(quality_report_file, 'w', encoding='utf-8') as f:
            json.dump(quality_report.dict(), f, indent=2, ensure_ascii=False, default=str)
        run_logger.metadata.output_files.append(str(quality_report_file))

        # Save run messages (skip in dry run)
        if not dry_run:
            output_file = run_logger.run_dir / "messages.jsonl"
            save_to_jsonl(all_run_messages, output_file)
            run_logger.metadata.output_files.append(str(output_file))

        # Save scraping log
        scraping_log_file = run_logger.run_dir / "scraping_log.json"
        scraping_log = {
            "chats_attempted": run_logger.metadata.chats_attempted,
            "chats_succeeded": run_logger.metadata.chats_succeeded,
            "chats_failed": run_logger.metadata.chats_failed,
            "chats_skipped": run_logger.metadata.chats_skipped,
            "total_messages_scraped": run_logger.metadata.total_messages_scraped,
            "chat_statuses": [status.model_dump() for status in chat_statuses]
        }
        with open(scraping_log_file, 'w', encoding='utf-8') as f:
            json.dump(scraping_log, f, indent=2, ensure_ascii=False)
        run_logger.metadata.output_files.append(str(scraping_log_file))

        # Save failed chats for retry (skip in dry run)
        failed_chats = [status for status in chat_statuses if status.status == "failed"]
        if failed_chats and not dry_run:
            failed_chats_file = run_logger.run_dir / "failed_chats.jsonl"
            with open(failed_chats_file, 'w', encoding='utf-8') as f:
                for status in failed_chats:
                    f.write(json.dumps({
                        "chat_id": status.chat_id,
                        "reason": status.error,
                        "message_count": status.message_count,
                        "scroll_iterations": status.scroll_count,
                        "api_calls": status.api_calls
                    }, ensure_ascii=False) + '\n')
            run_logger.metadata.output_files.append(str(failed_chats_file))
            logger.warning(f"Saved {len(failed_chats)} failed chats to {failed_chats_file}")

        # Finalize
        status = "completed" if not dry_run else "dry_run_completed"
        run_dir = run_logger.finalize(status)

        logger.success(f"\n{'='*60}")
        logger.success(f"Message scraping complete!")
        logger.success(f"Chats succeeded: {run_logger.metadata.chats_succeeded}/{run_logger.metadata.chats_attempted}")
        if run_logger.metadata.chats_failed > 0:
            logger.warning(f"Chats failed: {run_logger.metadata.chats_failed} (saved to failed_chats.jsonl for retry)")
        logger.success(f"Total messages: {run_logger.metadata.total_messages_scraped}")
        logger.success(f"Results saved to: {run_dir}")
        logger.success(f"{'='*60}")

        return run_dir

    except Exception as e:
        logger.error(f"Message scraping failed: {e}")
        run_logger.finalize("failed")
        raise
