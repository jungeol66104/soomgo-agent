"""Message grouping logic for simulation."""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional

from src.models import MessageItem
from src.simulation.models import MessageGroup


def find_start_trigger(messages: List[MessageItem]) -> Optional[int]:
    """Find the index of the start trigger message.
    
    Start trigger: System message containing "견적을 조회하였습니다"
    
    Returns:
        Index of the start trigger message, or None if not found.
    """
    for idx, msg in enumerate(messages):
        # System messages have user.id == 0
        if msg.user.id == 0 and "견적을 조회하였습니다" in msg.message:
            return idx
    
    return None


def find_end_trigger(messages: List[MessageItem], start_idx: int) -> Tuple[Optional[int], str]:
    """Find the index of the end trigger message.
    
    End trigger: System message containing "결제를 기다리는 중입니다"
    
    Returns:
        Tuple of (index, trigger_type) where trigger_type is:
        - "natural": Found the natural end trigger
        - "none": Reached end of messages without trigger
    """
    for idx in range(start_idx + 1, len(messages)):
        msg = messages[idx]
        # System messages have user.id == 0
        if msg.user.id == 0 and "결제를 기다리는 중입니다" in msg.message:
            return idx, "natural"
    
    # No end trigger found
    return None, "none"


def is_customer_message(msg: MessageItem) -> bool:
    """Check if message is from customer (not provider, not system)."""
    # System messages
    if msg.user.id == 0:
        return False
    
    # Provider messages
    if msg.user.provider and msg.user.provider.id is not None:
        return False
    
    # Customer message
    return True


def group_customer_messages(
    messages: List[MessageItem],
    start_idx: int,
    end_idx: Optional[int],
    time_window_seconds: int = 60
) -> List[MessageGroup]:
    """Group customer messages by time windows.
    
    Args:
        messages: All messages in the chat
        start_idx: Index of start trigger
        end_idx: Index of end trigger (or None for end of list)
        time_window_seconds: Time window for grouping (default 60s)
    
    Returns:
        List of MessageGroup objects
    """
    groups = []
    
    # Determine range to process
    end_range = end_idx if end_idx is not None else len(messages)
    
    # Find first customer message after start trigger
    current_idx = start_idx + 1
    while current_idx < end_range:
        msg = messages[current_idx]
        
        if is_customer_message(msg):
            # Start a new group
            group_messages = [msg]
            group_start_time = datetime.fromisoformat(msg.created_at.replace('Z', '+00:00'))
            group_end_time = group_start_time + timedelta(seconds=time_window_seconds)
            last_idx = current_idx
            
            # Collect all customer messages within time window
            for next_idx in range(current_idx + 1, end_range):
                next_msg = messages[next_idx]
                
                if is_customer_message(next_msg):
                    msg_time = datetime.fromisoformat(next_msg.created_at.replace('Z', '+00:00'))
                    
                    if msg_time <= group_end_time:
                        # Within time window
                        group_messages.append(next_msg)
                        last_idx = next_idx
                    else:
                        # Outside time window, stop collecting
                        break
            
            # Create MessageGroup
            actual_end_time = datetime.fromisoformat(group_messages[-1].created_at.replace('Z', '+00:00'))
            groups.append(MessageGroup(
                messages=group_messages,
                start_time=group_start_time,
                end_time=actual_end_time,
                last_message_index=last_idx
            ))
            
            # Move to next message after this group
            current_idx = last_idx + 1
        else:
            # Not a customer message, skip
            current_idx += 1
    
    return groups
