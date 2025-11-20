"""Utility functions for scraping."""

import asyncio
import json
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set
from loguru import logger
from playwright.async_api import Page

from .models import ScrapingRunMetadata, ChatListScrapingRunMetadata, ChatItem


class RunLogger:
    """Manages logging and metadata for a scraping run."""

    def __init__(self, run_type: str, config: Dict[str, Any] = None):
        self.run_id = str(uuid.uuid4())[:8]  # Short ID
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.run_dir = Path(f"data/runs/{timestamp}_{run_type}_{self.run_id}")
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.run_dir / "api_responses").mkdir(exist_ok=True)
        (self.run_dir / "screenshots").mkdir(exist_ok=True)

        # Set up file logging
        log_file = self.run_dir / "run.log"
        logger.add(log_file, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")

        # Initialize metadata based on run type
        if run_type in ["chat_list", "chat_list_dryrun"]:
            self.metadata = ChatListScrapingRunMetadata(
                run_id=self.run_id,
                run_type=run_type,
                started_at=datetime.now(),
                status="in_progress",
                config=config or {}
            )
        else:
            self.metadata = ScrapingRunMetadata(
                run_id=self.run_id,
                run_type=run_type,
                started_at=datetime.now(),
                status="in_progress",
                config=config or {}
            )

        logger.info(f"Run started: {self.run_id} ({run_type})")
        logger.info(f"Run directory: {self.run_dir}")

    def log_progress(self, processed: int, total: int = None):
        """Log progress update."""
        if total:
            percentage = (processed / total * 100)
            logger.info(f"Progress: {processed}/{total} ({percentage:.1f}%)")
        else:
            logger.info(f"Progress: {processed} items processed")

    def log_error(self, error: Exception, context: str):
        """Log an error with context."""
        error_info = {
            "error": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        self.metadata.errors.append(error_info)
        self.metadata.total_items_failed += 1
        logger.error(f"{context}: {error}")

    def log_warning(self, message: str):
        """Log a warning."""
        self.metadata.warnings.append(message)
        logger.warning(message)

    def save_api_response(self, response_data: Dict[str, Any], index: int):
        """Save raw API response."""
        response_file = self.run_dir / "api_responses" / f"response_{index:03d}.json"
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)

    async def save_screenshot(self, page: Page, name: str):
        """Save a screenshot."""
        screenshot_file = self.run_dir / "screenshots" / f"{name}.png"
        await page.screenshot(path=str(screenshot_file))
        logger.debug(f"Screenshot saved: {name}.png")

    def finalize(self, status: str = "completed"):
        """Finalize the run and save metadata."""
        self.metadata.completed_at = datetime.now()
        self.metadata.status = status

        # Calculate duration and rate
        duration = (self.metadata.completed_at - self.metadata.started_at).total_seconds()
        self.metadata.duration_seconds = duration

        if self.metadata.total_items_processed > 0 and duration > 0:
            self.metadata.items_per_second = self.metadata.total_items_processed / duration

        # Save summary
        summary_file = self.run_dir / "run_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata.dict(), f, indent=2, ensure_ascii=False, default=str)

        logger.success(f"Run completed: {self.run_id}")
        logger.info(f"Duration: {duration:.1f}s")
        logger.info(f"Items processed: {self.metadata.total_items_processed}")
        if self.metadata.total_items_failed > 0:
            logger.warning(f"Items failed: {self.metadata.total_items_failed}")

        return self.run_dir


class ChatListTracker:
    """Tracks chat list items and handles deduplication."""

    def __init__(self):
        self.seen_ids: Set[int] = set()
        self.all_chats: List[Dict[str, Any]] = []
        self.duplicate_count: int = 0

    def add_chat(self, chat: ChatItem) -> bool:
        """
        Add a chat item if not already seen.

        Returns:
            True if chat was new and added, False if duplicate
        """
        if chat.id in self.seen_ids:
            self.duplicate_count += 1
            return False

        self.seen_ids.add(chat.id)
        self.all_chats.append(chat.dict())
        return True

    def add_chats_from_response(self, response: Dict[str, Any]) -> int:
        """
        Add chats from an API response.

        Returns:
            Number of new chats added
        """
        new_count = 0
        results = response.get("results", [])

        for chat_data in results:
            try:
                chat = ChatItem(**chat_data)
                if self.add_chat(chat):
                    new_count += 1
            except Exception as e:
                logger.error(f"Failed to parse chat: {e}")

        return new_count

    def save_checkpoint(self, filepath: Path):
        """Save current state to checkpoint file."""
        checkpoint_data = {
            "seen_ids": list(self.seen_ids),
            "chat_count": len(self.all_chats),
            "timestamp": datetime.now().isoformat()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2)
        logger.debug(f"Checkpoint saved: {len(self.all_chats)} chats")

    def load_checkpoint(self, filepath: Path):
        """Load state from checkpoint file."""
        if not filepath.exists():
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)

        self.seen_ids = set(checkpoint_data.get("seen_ids", []))
        logger.info(f"Checkpoint loaded: {len(self.seen_ids)} previously seen chats")


def save_to_jsonl(data: List[Dict[str, Any]], filepath: Path):
    """Save data to JSONL file (one JSON object per line)."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')
    logger.success(f"Saved {len(data)} items to {filepath}")


def append_to_jsonl(item: Dict[str, Any], filepath: Path):
    """Append a single item to JSONL file."""
    with open(filepath, 'a', encoding='utf-8') as f:
        json_line = json.dumps(item, ensure_ascii=False)
        f.write(json_line + '\n')


async def scroll_to_bottom(page: Page, wait_time: int = 2000):
    """Scroll to the bottom of the page."""
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(wait_time)


async def wait_for_network_idle(page: Page, timeout: int = 5000):
    """Wait for network to become idle."""
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception as e:
        logger.debug(f"Network idle timeout: {e}")


def extract_service_titles(chats: List[Dict[str, Any]]) -> List[str]:
    """Extract unique service titles from chats."""
    services = set()
    for chat in chats:
        service_title = chat.get("service", {}).get("title")
        if service_title:
            services.add(service_title)
    return sorted(list(services))


def get_date_range(chats: List[Dict[str, Any]]) -> tuple[str, str]:
    """Get the oldest and newest chat activity dates (using updated_at)."""
    if not chats:
        return None, None

    dates = []
    for chat in chats:
        # Use updated_at since chat list is sorted by most recent activity
        updated_at = chat.get("updated_at")
        if updated_at:
            dates.append(updated_at)

    if not dates:
        return None, None

    dates.sort()
    return dates[0], dates[-1]  # oldest activity, newest activity


# ===== Humanization Functions =====

class HumanizationTracker:
    """Tracks humanization statistics"""
    def __init__(self):
        self.reading_pauses = 0
        self.scroll_ups = 0
        self.mouse_movements = 0
        self.session_breaks = 0
        self.total_wait_time = 0.0


async def humanized_scroll(page: Page, tracker: HumanizationTracker = None):
    """
    Scroll to bring the Intersection Observer sentinel into view.
    This triggers the infinite scroll loader properly.
    """
    import time
    start_time = time.time()

    # 1. Find and scroll the observer element into view
    # This is what actually triggers the API call for infinite scroll
    observer_found = await page.evaluate("""
        () => {
            const observer = document.querySelector('.observer-container');
            if (observer) {
                observer.scrollIntoView({ behavior: 'smooth', block: 'end' });
                return true;
            }
            return false;
        }
    """)

    if not observer_found:
        # Fallback: if no observer found, scroll to bottom
        logger.debug("No observer found, scrolling to bottom as fallback")
        await page.evaluate("""
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            })
        """)

    # 2. Random wait time (1.5 to 4 seconds) for scroll to complete and trigger
    wait_time = random.randint(1500, 4000)
    await page.wait_for_timeout(wait_time)

    # 3. Occasionally pause longer (like reading)
    if random.random() < 0.2:  # 20% chance
        logger.debug("Pausing to 'read'...")
        pause_time = random.randint(2000, 4000)
        await page.wait_for_timeout(pause_time)
        if tracker:
            tracker.reading_pauses += 1

    # 4. Sometimes scroll up a bit (like checking something)
    if random.random() < 0.15:  # 15% chance
        logger.debug("Scrolling up slightly...")
        scroll_up = random.randint(100, 300)
        await page.evaluate(f"window.scrollBy(0, -{scroll_up})")
        await page.wait_for_timeout(random.randint(500, 1500))
        if tracker:
            tracker.scroll_ups += 1

    if tracker:
        tracker.total_wait_time += (time.time() - start_time)


async def move_mouse_randomly(page: Page, tracker: HumanizationTracker = None):
    """Occasionally move mouse to look more human."""
    if random.random() < 0.3:  # 30% chance
        x = random.randint(200, 800)
        y = random.randint(100, 600)
        await page.mouse.move(x, y)
        if tracker:
            tracker.mouse_movements += 1


async def random_session_break(page: Page, tracker: HumanizationTracker = None):
    """
    Occasionally take a longer break (like human taking coffee/bathroom break).
    10-30 second pause.
    """
    if random.random() < 0.05:  # 5% chance
        break_time = random.randint(10000, 30000)
        logger.info(f"Taking a session break ({break_time/1000:.1f}s)...")
        await page.wait_for_timeout(break_time)
        if tracker:
            tracker.session_breaks += 1
            tracker.total_wait_time += (break_time / 1000)


async def randomize_viewport(page: Page):
    """Randomize browser viewport size to avoid fingerprinting."""
    widths = [1280, 1366, 1440, 1536, 1920]
    heights = [720, 768, 900, 960, 1080]

    width = random.choice(widths)
    height = random.choice(heights)

    await page.set_viewport_size({"width": width, "height": height})
    logger.debug(f"Viewport set to {width}x{height}")


async def apply_rate_limit(min_delay: float = 2.0, max_delay: float = 5.0):
    """
    Apply rate limiting between actions.

    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"Rate limiting: waiting {delay:.2f}s")
    await asyncio.sleep(delay)


async def exponential_backoff(attempt: int, base_delay: float = 5.0):
    """
    Apply exponential backoff for rate limit errors.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds
    """
    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
    max_delay = 60.0  # Cap at 60 seconds
    delay = min(delay, max_delay)

    logger.warning(f"Exponential backoff: waiting {delay:.1f}s (attempt #{attempt + 1})")
    await asyncio.sleep(delay)


async def random_pause(page: Page, min_ms: int = 500, max_ms: int = 2000):
    """Random pause between actions."""
    pause_time = random.randint(min_ms, max_ms)
    await page.wait_for_timeout(pause_time)
