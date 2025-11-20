"""Pydantic models for DSPy prompt optimization."""

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class OptimizationConfig(BaseModel):
    """Configuration for DSPy prompt optimization."""

    model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use for optimization",
    )
    approach: Literal["few-shot", "instruction-only"] = Field(
        default="few-shot",
        description="Optimization approach",
    )
    max_examples: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Maximum number of examples in final prompt",
    )
    optimizer: Literal["BootstrapFewShot", "SignatureOptimizer", "MIPRO"] = Field(
        default="BootstrapFewShot",
        description="DSPy optimizer to use",
    )
    train_split: float = Field(
        default=0.8,
        ge=0.1,
        le=0.9,
        description="Fraction of data for training (rest is validation)",
    )
    dry_run: bool = Field(
        default=False,
        description="Preview only, don't run optimization",
    )
    # Filtering options
    min_response_length: int = Field(
        default=50,
        ge=0,
        description="Minimum response length in characters (filters out short responses)",
    )
    max_turn_number: Optional[int] = Field(
        default=20,
        description="Maximum turn number to include (focuses on early conversation)",
    )
    sample_chats: Optional[int] = Field(
        default=None,
        description="Number of chats to randomly sample (None = use all)",
    )


class TrainingExample(BaseModel):
    """A single training example for DSPy."""

    conversation_history: str = Field(
        description="Conversation history up to this point",
    )
    provider_response: str = Field(
        description="Provider's response at this turn",
    )
    chat_id: int = Field(
        description="ID of the source chat",
    )
    service_type: str = Field(
        description="Type of service requested",
    )
    turn_number: int = Field(
        description="Turn number in the conversation",
    )


class OptimizationResult(BaseModel):
    """Results from DSPy optimization."""

    run_id: str = Field(
        description="Unique run identifier",
    )
    run_type: str = Field(
        default="prompt_optimize",
        description="Type of run",
    )
    started_at: datetime = Field(
        description="When optimization started",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When optimization completed",
    )
    status: Literal["running", "completed", "failed"] = Field(
        default="running",
        description="Status of the optimization",
    )
    config: OptimizationConfig = Field(
        description="Configuration used",
    )
    data_stats: dict = Field(
        default_factory=dict,
        description="Statistics about the data",
    )
    results: dict = Field(
        default_factory=dict,
        description="Optimization results and metrics",
    )
    output_dir: Path = Field(
        description="Directory where outputs are saved",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed",
    )


class ConversationData(BaseModel):
    """Structured conversation data from a single chat."""

    chat_id: int
    service_type: str
    is_hired: bool
    price: Optional[int]
    messages: list[dict]  # Raw message objects
    provider_turn_count: int
    customer_turn_count: int
