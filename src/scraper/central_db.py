"""Central database manager for maintaining a deduplicated master chat list."""

import json
from pathlib import Path
from typing import Dict, List
from loguru import logger

from src.models import ChatItem


class CentralChatDatabase:
    """Manages the central chat_list_master.jsonl database."""

    def __init__(self, db_path: str = "data/chat_list_master.jsonl"):
        """Initialize the central database manager.

        Args:
            db_path: Path to the central database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[int, ChatItem]:
        """Load all chats from the central database.

        Returns:
            Dictionary mapping chat_id -> ChatItem
        """
        chats = {}

        if not self.db_path.exists():
            logger.info(f"Central database not found at {self.db_path}, will create new one")
            return chats

        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        chat_data = json.loads(line)
                        chat = ChatItem(**chat_data)
                        chats[chat.id] = chat
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line {line_num} in central DB: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to create ChatItem from line {line_num}: {e}")

            logger.info(f"Loaded {len(chats)} chats from central database")
            return chats

        except Exception as e:
            logger.error(f"Error loading central database: {e}")
            return chats

    def merge_and_update(
        self,
        existing: Dict[int, ChatItem],
        new_chats: List[ChatItem]
    ) -> tuple[Dict[int, ChatItem], int, int]:
        """Merge new chats into existing database.

        Args:
            existing: Current chats in database (chat_id -> ChatItem)
            new_chats: New chats from latest scraping run

        Returns:
            Tuple of (merged_chats, new_count, updated_count)
        """
        merged = existing.copy()
        new_count = 0
        updated_count = 0

        for chat in new_chats:
            if chat.id in merged:
                # Chat exists - update it
                merged[chat.id] = chat
                updated_count += 1
            else:
                # New chat - add it
                merged[chat.id] = chat
                new_count += 1

        logger.info(f"Merge complete: {new_count} new chats, {updated_count} updated chats")
        return merged, new_count, updated_count

    def save(self, chats: Dict[int, ChatItem]) -> None:
        """Save all chats to the central database.

        Args:
            chats: Dictionary of chat_id -> ChatItem to save
        """
        try:
            # Sort by chat ID for consistent ordering
            sorted_chats = sorted(chats.values(), key=lambda c: c.id)

            # Write to temp file first, then rename (atomic operation)
            temp_path = self.db_path.with_suffix('.tmp')

            with open(temp_path, 'w', encoding='utf-8') as f:
                for chat in sorted_chats:
                    json_line = chat.model_dump_json() + '\n'
                    f.write(json_line)

            # Atomic rename
            temp_path.replace(self.db_path)

            logger.info(f"Saved {len(chats)} chats to central database at {self.db_path}")

        except Exception as e:
            logger.error(f"Error saving central database: {e}")
            raise

    def get_stats(self) -> Dict:
        """Get statistics about the central database.

        Returns:
            Dictionary with stats about the database
        """
        chats = self.load()

        if not chats:
            return {
                "total_chats": 0,
                "oldest_chat": None,
                "newest_chat": None,
                "unique_services": []
            }

        chat_list = list(chats.values())

        # Get date range
        oldest = min(chat_list, key=lambda c: c.created_at)
        newest = max(chat_list, key=lambda c: c.updated_at)

        # Get unique services
        services = set(chat.service.title for chat in chat_list)

        return {
            "total_chats": len(chats),
            "oldest_chat": oldest.created_at,
            "newest_chat": newest.updated_at,
            "unique_services": sorted(services)
        }
