"""Format conversation data for DSPy training."""

from loguru import logger

from .models import ConversationData, TrainingExample


def is_provider_message(message: dict) -> bool:
    """Check if message is from the provider."""
    return message.get("user", {}).get("provider") is not None


def format_conversation(conversation: ConversationData) -> str:
    """
    Format a conversation into simple chat format.

    Format:
        Customer: [message]
        Provider: [message]
        Customer: [message]
        ...

    Args:
        conversation: ConversationData object

    Returns:
        Formatted conversation string
    """
    lines = []

    for message in conversation.messages:
        role = "Provider" if is_provider_message(message) else "Customer"
        content = message.get("message", "").strip()

        if content:  # Only include non-empty messages
            lines.append(f"{role}: {content}")

    return "\n".join(lines)


def create_training_examples(
    conversations: list[ConversationData],
    min_response_length: int = 0,
    max_turn_number: int = None,
) -> list[TrainingExample]:
    """
    Create turn-by-turn training examples from conversations.

    Each provider response becomes a separate training example with
    the conversation history up to that point as input.

    Args:
        conversations: List of ConversationData objects
        min_response_length: Minimum length for provider responses (filters short ones)
        max_turn_number: Maximum turn number to include (None = no limit)

    Returns:
        List of TrainingExample objects
    """
    training_examples = []

    for conversation in conversations:
        # Build conversation incrementally
        history_lines = []
        provider_turn = 0

        for message in conversation.messages:
            role = "Provider" if is_provider_message(message) else "Customer"
            content = message.get("message", "").strip()

            if not content:
                continue

            # If this is a provider message, create a training example
            if is_provider_message(message):
                provider_turn += 1

                # Apply filters
                if max_turn_number is not None and provider_turn > max_turn_number:
                    break  # Stop processing this conversation

                if len(content) < min_response_length:
                    # Skip short responses but continue building history
                    history_lines.append(f"{role}: {content}")
                    continue

                # Create example with history so far
                conversation_history = "\n".join(history_lines)

                example = TrainingExample(
                    conversation_history=conversation_history,
                    provider_response=content,
                    chat_id=conversation.chat_id,
                    service_type=conversation.service_type,
                    turn_number=provider_turn,
                )

                training_examples.append(example)

            # Add this message to history for next turn
            history_lines.append(f"{role}: {content}")

    logger.info(
        f"Created {len(training_examples)} training examples from "
        f"{len(conversations)} conversations"
    )

    return training_examples


def format_example_for_display(example: TrainingExample) -> str:
    """
    Format a training example for human-readable display.

    Args:
        example: TrainingExample object

    Returns:
        Formatted string for display
    """
    return f"""
--- Training Example (Chat {example.chat_id}, Turn {example.turn_number}) ---
Service: {example.service_type}

Conversation History:
{example.conversation_history}

Provider Response:
{example.provider_response}
---
""".strip()


def get_example_stats(examples: list[TrainingExample]) -> dict:
    """
    Get statistics about training examples.

    Args:
        examples: List of TrainingExample objects

    Returns:
        Dictionary of statistics
    """
    if not examples:
        return {
            "total_examples": 0,
            "unique_chats": 0,
            "avg_history_length": 0,
            "avg_response_length": 0,
            "service_distribution": {},
        }

    unique_chats = len(set(ex.chat_id for ex in examples))

    history_lengths = [len(ex.conversation_history) for ex in examples]
    response_lengths = [len(ex.provider_response) for ex in examples]

    avg_history_length = sum(history_lengths) / len(examples)
    avg_response_length = sum(response_lengths) / len(examples)

    # Service type distribution
    service_counts = {}
    for ex in examples:
        service_counts[ex.service_type] = service_counts.get(ex.service_type, 0) + 1

    return {
        "total_examples": len(examples),
        "unique_chats": unique_chats,
        "avg_history_length": round(avg_history_length, 1),
        "avg_response_length": round(avg_response_length, 1),
        "service_distribution": service_counts,
        "examples_per_chat": round(len(examples) / unique_chats, 1)
        if unique_chats > 0
        else 0,
    }
