"""Data models for simulation system."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.models import MessageItem


class MessageGroup(BaseModel):
    """Group of customer messages within a time window."""
    messages: List[MessageItem]
    start_time: datetime
    end_time: datetime
    last_message_index: int  # Index in original message list

    @property
    def combined_message(self) -> str:
        """Combine all messages in group."""
        return "\n".join([m.message for m in self.messages])

    @property
    def duration_seconds(self) -> float:
        """Duration of this message group."""
        return (self.end_time - self.start_time).total_seconds()


class SimulatedMessage(BaseModel):
    """A simulated agent response in original message format."""
    id: int  # Negative ID to distinguish from real messages
    user: Dict[str, Any]
    type: str
    own_type: str  # "SIMULATED" or "SIMULATED_PAYMENT"
    message: str
    created_at: str
    is_receiver_read: bool = False
    system: Optional[Dict[str, Any]] = None
    file: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None
    nonce: Optional[str] = None
    calendar: Optional[Dict[str, Any]] = None
    auto_message: Optional[Dict[str, Any]] = None
    call_data: Optional[Dict[str, Any]] = None


class SimulationMetadata(BaseModel):
    """Metadata for a simulation run."""
    run_id: str
    chat_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "running", "completed", "failed"
    total_customer_groups: int = 0
    total_simulated_responses: int = 0
    duration_seconds: Optional[float] = None

    # Configuration
    time_window_seconds: int = 60
    agent_config: Dict[str, Any] = Field(default_factory=dict)

    # Start/end trigger info
    start_trigger_found: bool = False
    start_trigger_index: int = -1
    end_trigger_type: str = "none"  # "natural", "agent_generated", "none"

    # Errors
    errors: List[str] = Field(default_factory=list)

    # Progress tracking
    current_group: int = 0

    @property
    def progress(self) -> float:
        """Calculate progress as 0.0 to 1.0."""
        if self.total_customer_groups == 0:
            return 0.0
        return min(1.0, self.current_group / self.total_customer_groups)

    @property
    def progress_text(self) -> str:
        """Human readable progress."""
        return f"Turn {self.current_group}/{self.total_customer_groups}"


class SimulationRun(BaseModel):
    """Complete simulation run data."""
    metadata: SimulationMetadata
    simulated_messages: List[SimulatedMessage] = Field(default_factory=list)
