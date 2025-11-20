"""Load and filter chat data for DSPy training."""

import json
from pathlib import Path
from typing import Optional

from loguru import logger

from .models import ConversationData


def load_hired_chats(
    chat_list_path: Path = Path("data/chat_list_master.jsonl"),
) -> list[dict]:
    """
    Load all hired chats from the master chat list.

    Args:
        chat_list_path: Path to chat_list_master.jsonl

    Returns:
        List of chat metadata dictionaries for hired chats
    """
    if not chat_list_path.exists():
        raise FileNotFoundError(f"Chat list not found: {chat_list_path}")

    hired_chats = []

    with open(chat_list_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            chat = json.loads(line)

            # Filter: is_hired == true
            if chat.get("quote", {}).get("is_hired", False):
                hired_chats.append(chat)

    logger.info(f"Loaded {len(hired_chats)} hired chats from {chat_list_path}")
    return hired_chats


def load_chat_messages(
    chat_id: int,
    messages_dir: Path = Path("data/messages"),
) -> list[dict]:
    """
    Load messages for a specific chat.

    Args:
        chat_id: Chat ID to load
        messages_dir: Directory containing message files

    Returns:
        List of message dictionaries
    """
    message_file = messages_dir / f"chat_{chat_id}.jsonl"

    if not message_file.exists():
        logger.warning(f"Message file not found for chat {chat_id}: {message_file}")
        return []

    messages = []

    with open(message_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            message = json.loads(line)
            messages.append(message)

    return messages


def filter_human_messages(messages: list[dict]) -> list[dict]:
    """
    Filter out system messages, keeping only human TEXT messages.

    Filters:
    - Exclude system messages (user.id == 0)
    - Keep only TEXT type messages
    - Keep chronological order

    Args:
        messages: List of raw message dictionaries

    Returns:
        Filtered list of human messages only
    """
    human_messages = []

    for msg in messages:
        # Skip system messages (숨고 알리미)
        if msg.get("user", {}).get("id") == 0:
            continue

        # Keep only TEXT messages (exclude files, images, etc.)
        if msg.get("type") != "TEXT":
            continue

        human_messages.append(msg)

    return human_messages


def load_conversation_data(
    chat_metadata: dict,
    messages_dir: Path = Path("data/messages"),
) -> Optional[ConversationData]:
    """
    Load complete conversation data for a hired chat.

    Args:
        chat_metadata: Chat metadata from chat_list_master.jsonl
        messages_dir: Directory containing message files

    Returns:
        ConversationData object or None if no valid messages
    """
    chat_id = chat_metadata["id"]

    # Load messages
    raw_messages = load_chat_messages(chat_id, messages_dir)

    if not raw_messages:
        logger.warning(f"No messages found for chat {chat_id}")
        return None

    # Filter to human TEXT messages only
    messages = filter_human_messages(raw_messages)

    if not messages:
        logger.warning(f"No human messages found for chat {chat_id}")
        return None

    # Count provider vs customer turns
    provider_turns = sum(
        1 for msg in messages if msg.get("user", {}).get("provider") is not None
    )
    customer_turns = len(messages) - provider_turns

    # Extract metadata
    service_type = chat_metadata.get("service", {}).get("title", "Unknown")
    price = chat_metadata.get("quote", {}).get("price")

    return ConversationData(
        chat_id=chat_id,
        service_type=service_type,
        is_hired=True,  # We only load hired chats
        price=price,
        messages=messages,
        provider_turn_count=provider_turns,
        customer_turn_count=customer_turns,
    )


def load_all_hired_conversations(
    chat_list_path: Path = Path("data/chat_list_master.jsonl"),
    messages_dir: Path = Path("data/messages"),
) -> list[ConversationData]:
    """
    Load all hired conversations with messages.

    Args:
        chat_list_path: Path to chat_list_master.jsonl
        messages_dir: Directory containing message files

    Returns:
        List of ConversationData objects
    """
    hired_chats = load_hired_chats(chat_list_path)
    conversations = []

    logger.info(f"Loading messages for {len(hired_chats)} hired chats...")

    for chat_metadata in hired_chats:
        conversation = load_conversation_data(chat_metadata, messages_dir)

        if conversation is not None:
            conversations.append(conversation)

    logger.info(f"Successfully loaded {len(conversations)} conversations with messages")

    return conversations
