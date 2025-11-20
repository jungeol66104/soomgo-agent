"""Storage layer for simulation data."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import json

from src.simulation.models import SimulationMetadata, SimulatedMessage, SimulationRun


class SimulationStorage:
    """Handle storage and retrieval of simulation data."""

    def __init__(self, base_dir: Path):
        """Initialize storage with base directory (data/simulations)."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_chat_dir(self, chat_id: int) -> Path:
        """Get directory for a specific chat's simulations."""
        chat_dir = self.base_dir / f"chat_{chat_id}"
        chat_dir.mkdir(parents=True, exist_ok=True)
        return chat_dir

    def _get_run_dir(self, chat_id: int, run_id: str) -> Path:
        """Get directory for a specific simulation run."""
        run_dir = self._get_chat_dir(chat_id) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def save_metadata(self, metadata: SimulationMetadata) -> None:
        """Save simulation metadata to metadata.json."""
        run_dir = self._get_run_dir(metadata.chat_id, metadata.run_id)
        metadata_file = run_dir / "metadata.json"
        
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def save_messages(self, chat_id: int, run_id: str, messages: List[SimulatedMessage]) -> None:
        """Save simulated messages to messages.jsonl."""
        run_dir = self._get_run_dir(chat_id, run_id)
        messages_file = run_dir / "messages.jsonl"
        
        with open(messages_file, "w", encoding="utf-8") as f:
            for msg in messages:
                json_line = json.dumps(msg.model_dump(mode="json"), ensure_ascii=False)
                f.write(json_line + "\n")

    def load_metadata(self, chat_id: int, run_id: str) -> Optional[SimulationMetadata]:
        """Load simulation metadata from metadata.json."""
        run_dir = self._get_run_dir(chat_id, run_id)
        metadata_file = run_dir / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return SimulationMetadata(**data)

    def load_messages(self, chat_id: int, run_id: str) -> List[SimulatedMessage]:
        """Load simulated messages from messages.jsonl."""
        run_dir = self._get_run_dir(chat_id, run_id)
        messages_file = run_dir / "messages.jsonl"
        
        if not messages_file.exists():
            return []
        
        messages = []
        with open(messages_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    messages.append(SimulatedMessage(**data))
        
        return messages

    def load_run(self, chat_id: int, run_id: str) -> Optional[SimulationRun]:
        """Load complete simulation run (metadata + messages)."""
        metadata = self.load_metadata(chat_id, run_id)
        if not metadata:
            return None
        
        messages = self.load_messages(chat_id, run_id)
        return SimulationRun(metadata=metadata, simulated_messages=messages)

    def list_runs(self, chat_id: int) -> List[str]:
        """List all simulation run IDs for a chat."""
        chat_dir = self._get_chat_dir(chat_id)
        
        if not chat_dir.exists():
            return []
        
        # Find all directories starting with "run_"
        runs = []
        for item in chat_dir.iterdir():
            if item.is_dir() and item.name.startswith("run_"):
                runs.append(item.name)
        
        # Sort by timestamp (newest first)
        runs.sort(reverse=True)
        return runs

    def get_run_summary(self, chat_id: int, run_id: str) -> Optional[Dict]:
        """Get summary info for a run (for UI display)."""
        metadata = self.load_metadata(chat_id, run_id)
        if not metadata:
            return None
        
        return {
            "run_id": run_id,
            "status": metadata.status,
            "progress": metadata.progress,
            "progress_text": metadata.progress_text,
            "started_at": metadata.started_at,
            "completed_at": metadata.completed_at,
            "duration_seconds": metadata.duration_seconds,
            "total_customer_groups": metadata.total_customer_groups,
            "total_simulated_responses": metadata.total_simulated_responses,
        }
