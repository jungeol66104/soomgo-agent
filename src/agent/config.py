"""Agent configuration."""

import os
from pathlib import Path
from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for the Soomgo agent."""

    # Model settings
    model: str = "gpt-4o-mini"
    temperature: float = 0.85
    max_tokens: int = 300

    # Prompt settings
    prompt_path: Path = Path("data/prompts/base_prompt.txt")

    # Data directories
    knowledge_dir: Path = Path("data/knowledge")

    # Behavior settings
    max_conversation_turns: int = 50

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment."""
        # Get base directory from environment (set by CLI)
        base_dir = Path(os.getenv("SOOMGO_BASE_DIR", "."))

        return cls(
            model=os.getenv("AGENT_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.7")),
            prompt_path=base_dir / "data" / "prompts" / "base_prompt.txt",
            knowledge_dir=base_dir / "data" / "knowledge",
        )
