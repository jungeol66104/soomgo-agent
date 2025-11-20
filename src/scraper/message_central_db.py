"""Central database manager for per-chat message files."""

import json
from pathlib import Path
from typing import Dict, List
from loguru import logger

from src.models import MessageItem


class MessageCentralDB:
    """Manages per-chat message master files in data/messages/ directory."""

    def __init__(self, messages_dir: str = "data/messages"):
        """Initialize the message central database manager.

        Args:
            messages_dir: Path to the messages directory
        """
        self.messages_dir = Path(messages_dir)
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    def get_chat_file_path(self, chat_id: int) -> Path:
        """Get the file path for a specific chat's messages.

        Args:
            chat_id: ID of the chat

        Returns:
            Path to the chat's message file
        """
        return self.messages_dir / f"chat_{chat_id}.jsonl"

    def load_chat_messages(self, chat_id: int) -> Dict[int, MessageItem]:
        """Load all messages for a specific chat.

        Args:
            chat_id: ID of the chat

        Returns:
            Dictionary mapping message_id -> MessageItem
        """
        messages = {}
        file_path = self.get_chat_file_path(chat_id)

        if not file_path.exists():
            logger.info(f"No existing messages file for chat {chat_id}")
            return messages

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        message_data = json.loads(line)
                        message = MessageItem(**message_data)
                        messages[message.id] = message
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line {line_num} in chat {chat_id}: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to create MessageItem from line {line_num}: {e}")

            logger.info(f"Loaded {len(messages)} messages for chat {chat_id}")
            return messages

        except Exception as e:
            logger.error(f"Error loading messages for chat {chat_id}: {e}")
            return messages

    def merge_and_update(
        self,
        chat_id: int,
        existing: Dict[int, MessageItem],
        new_messages: List[MessageItem]
    ) -> tuple[Dict[int, MessageItem], int, int]:
        """Merge new messages into existing messages for a chat.

        Args:
            chat_id: ID of the chat
            existing: Current messages in database (message_id -> MessageItem)
            new_messages: New messages from latest scraping run

        Returns:
            Tuple of (merged_messages, new_count, updated_count)
        """
        merged = existing.copy()
        new_count = 0
        updated_count = 0

        for message in new_messages:
            if message.id in merged:
                # Message exists - update it (in case of edits or status changes)
                merged[message.id] = message
                updated_count += 1
            else:
                # New message - add it
                merged[message.id] = message
                new_count += 1

        logger.info(f"Chat {chat_id}: {new_count} new, {updated_count} updated messages")
        return merged, new_count, updated_count

    def save_chat_messages(self, chat_id: int, messages: Dict[int, MessageItem]) -> None:
        """Save all messages for a specific chat.

        Args:
            chat_id: ID of the chat
            messages: Dictionary of message_id -> MessageItem to save
        """
        file_path = self.get_chat_file_path(chat_id)

        try:
            # Sort by created_at timestamp (chronological order)
            sorted_messages = sorted(messages.values(), key=lambda m: m.created_at)

            # Write to temp file first, then rename (atomic operation)
            temp_path = file_path.with_suffix('.tmp')

            with open(temp_path, 'w', encoding='utf-8') as f:
                for message in sorted_messages:
                    json_line = message.model_dump_json() + '\n'
                    f.write(json_line)

            # Atomic rename
            temp_path.replace(file_path)

            logger.info(f"Saved {len(messages)} messages for chat {chat_id} to {file_path}")

        except Exception as e:
            logger.error(f"Error saving messages for chat {chat_id}: {e}")
            raise

    def chat_exists(self, chat_id: int) -> bool:
        """Check if messages file exists for a chat.

        Args:
            chat_id: ID of the chat

        Returns:
            True if chat messages file exists
        """
        return self.get_chat_file_path(chat_id).exists()

    def get_message_count(self, chat_id: int) -> int:
        """Get the number of messages stored for a chat.

        Args:
            chat_id: ID of the chat

        Returns:
            Number of messages
        """
        messages = self.load_chat_messages(chat_id)
        return len(messages)

    def get_stats(self) -> Dict:
        """Get statistics about all stored chat messages.

        Returns:
            Dictionary with stats about the message database
        """
        chat_files = list(self.messages_dir.glob("chat_*.jsonl"))
        total_chats = len(chat_files)
        total_messages = 0

        for chat_file in chat_files:
            try:
                with open(chat_file, 'r', encoding='utf-8') as f:
                    message_count = sum(1 for line in f if line.strip())
                    total_messages += message_count
            except Exception as e:
                logger.warning(f"Error reading {chat_file}: {e}")

        return {
            "total_chats_with_messages": total_chats,
            "total_messages": total_messages,
            "avg_messages_per_chat": total_messages / total_chats if total_chats > 0 else 0
        }
