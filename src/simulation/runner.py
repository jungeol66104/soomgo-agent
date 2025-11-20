"""High-level simulation runner interface."""

import asyncio
from pathlib import Path
from typing import Optional, List

from src.scraper.message_central_db import MessageCentralDB
from src.simulation.simulator import Simulator
from src.simulation.storage import SimulationStorage
from src.simulation.models import SimulationRun


class SimulationRunner:
    """High-level interface for running simulations."""

    def __init__(self, messages_dir: Path, simulations_dir: Path):
        """Initialize runner.
        
        Args:
            messages_dir: Path to messages directory
            simulations_dir: Path to simulations directory
        """
        self.message_db = MessageCentralDB(str(messages_dir))
        self.storage = SimulationStorage(simulations_dir)

    def run_simulation(
        self,
        chat_id: int,
        time_window_seconds: int = 60,
        agent=None
    ) -> SimulationRun:
        """Run a simulation for a chat.
        
        Args:
            chat_id: ID of chat to simulate
            time_window_seconds: Time window for grouping messages
            agent: Optional agent instance
            
        Returns:
            SimulationRun with results
        """
        # Load messages
        messages_dict = self.message_db.load_chat_messages(chat_id)
        if not messages_dict:
            raise ValueError(f"No messages found for chat {chat_id}")
        
        # Sort messages by ID
        messages = sorted(messages_dict.values(), key=lambda m: m.id)
        
        # Create and run simulator
        simulator = Simulator(
            chat_id=chat_id,
            messages=messages,
            storage=self.storage,
            time_window_seconds=time_window_seconds
        )
        
        return simulator.run(agent=agent)

    async def run_simulation_async(
        self,
        chat_id: int,
        time_window_seconds: int = 60,
        agent=None
    ) -> SimulationRun:
        """Run simulation asynchronously (for background execution).
        
        Args:
            chat_id: ID of chat to simulate
            time_window_seconds: Time window for grouping messages
            agent: Optional agent instance
            
        Returns:
            SimulationRun with results
        """
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.run_simulation,
            chat_id,
            time_window_seconds,
            agent
        )

    def list_chat_runs(self, chat_id: int) -> List[str]:
        """List all simulation runs for a chat.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            List of run IDs (sorted newest first)
        """
        return self.storage.list_runs(chat_id)

    def get_run(self, chat_id: int, run_id: str) -> Optional[SimulationRun]:
        """Load a simulation run.
        
        Args:
            chat_id: Chat ID
            run_id: Run ID
            
        Returns:
            SimulationRun or None if not found
        """
        return self.storage.load_run(chat_id, run_id)

    def get_run_summary(self, chat_id: int, run_id: str) -> Optional[dict]:
        """Get summary info for a run.
        
        Args:
            chat_id: Chat ID
            run_id: Run ID
            
        Returns:
            Summary dict or None if not found
        """
        return self.storage.get_run_summary(chat_id, run_id)
