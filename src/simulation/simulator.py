"""Core simulation engine."""

from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from loguru import logger

from src.models import MessageItem
from src.simulation.models import (
    MessageGroup,
    SimulatedMessage,
    SimulationMetadata,
    SimulationRun
)
from src.simulation.grouper import (
    find_start_trigger,
    find_end_trigger,
    group_customer_messages
)
from src.simulation.storage import SimulationStorage


class Simulator:
    """Simulation engine for running agent against historical chats."""

    def __init__(
        self,
        chat_id: int,
        messages: List[MessageItem],
        storage: SimulationStorage,
        time_window_seconds: int = 60
    ):
        """Initialize simulator.
        
        Args:
            chat_id: ID of the chat being simulated
            messages: All messages in the chat (sorted by ID)
            storage: Storage instance for saving results
            time_window_seconds: Time window for grouping customer messages
        """
        self.chat_id = chat_id
        self.messages = messages
        self.storage = storage
        self.time_window_seconds = time_window_seconds
        
        # Generate run ID
        self.run_id = f"run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        
        # Initialize metadata
        self.metadata = SimulationMetadata(
            run_id=self.run_id,
            chat_id=chat_id,
            started_at=datetime.now(),
            status="running",
            time_window_seconds=time_window_seconds
        )
        
        # Simulated messages
        self.simulated_messages: List[SimulatedMessage] = []
        
        # Message ID counter (negative IDs for simulated messages)
        self.next_message_id = -1

    def _build_context(self, up_to_index: int) -> List[MessageItem]:
        """Build conversation context up to a specific message index.
        
        IMPORTANT: Only includes original messages, never simulated ones.
        
        Args:
            up_to_index: Build context up to (and including) this message index
            
        Returns:
            List of original messages for context
        """
        return self.messages[:up_to_index + 1]

    def _generate_response(
        self,
        context: List[MessageItem],
        customer_group: MessageGroup,
        agent=None
    ) -> str:
        """Generate agent response for a customer message group.

        Args:
            context: Conversation context (original messages only)
            customer_group: Customer message group to respond to
            agent: Optional SoomgoAgent instance

        Returns:
            Generated response text
        """
        # If no agent provided, return placeholder
        if agent is None:
            combined_message = customer_group.combined_message
            return f"[PLACEHOLDER - No agent provided. Customer said: {combined_message[:50]}...]"

        # Convert MessageItem context to conversation history format
        conversation_history = []
        for msg in context:
            # Skip system messages
            if msg.user.id == 0:
                continue

            # Determine if message is from customer or provider
            if msg.user.provider and msg.user.provider.id is not None:
                # Provider message
                conversation_history.append({
                    "role": "assistant",
                    "content": msg.message
                })
            else:
                # Customer message
                conversation_history.append({
                    "role": "user",
                    "content": msg.message
                })

        # Get the latest customer message from the group
        latest_message = customer_group.combined_message

        try:
            # Call agent
            response, _, _, _ = agent.chat(
                user_message=latest_message,
                conversation_history=conversation_history[:-1] if conversation_history else None,  # Exclude last message (it's the current one)
                gathered_info=None,  # Agent will extract this
                conversation_state="active",
                last_closure_response=None
            )

            logger.debug(f"Generated response: {len(response)} chars")
            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"[ERROR - Failed to generate response: {str(e)}]"

    def _create_simulated_message(
        self,
        content: str,
        reference_msg: MessageItem,
        is_payment: bool = False
    ) -> SimulatedMessage:
        """Create a simulated message in original format.
        
        Args:
            content: Message content
            reference_msg: Reference message for copying structure
            is_payment: Whether this is a payment message
            
        Returns:
            SimulatedMessage object
        """
        # Get provider info from reference (should be a provider message)
        # Find a provider message in context to use as template
        provider_user = None
        for msg in self.messages:
            if msg.user.provider and msg.user.provider.id is not None:
                provider_user = msg.user
                break
        
        if not provider_user:
            # Fallback: use reference message user
            provider_user = reference_msg.user
        
        message_id = self.next_message_id
        self.next_message_id -= 1
        
        return SimulatedMessage(
            id=message_id,
            user=provider_user.model_dump(),
            type="MESSAGE",
            own_type="SIMULATED_PAYMENT" if is_payment else "SIMULATED",
            message=content,
            created_at=datetime.now().isoformat() + "Z",
            is_receiver_read=False
        )

    def run(self, agent=None) -> SimulationRun:
        """Run the simulation.
        
        Args:
            agent: Optional agent instance (if None, uses placeholder)
            
        Returns:
            Complete simulation run data
        """
        try:
            # Find start trigger
            start_idx = find_start_trigger(self.messages)
            if start_idx is None:
                self.metadata.status = "failed"
                self.metadata.errors.append("Start trigger not found")
                self.metadata.completed_at = datetime.now()
                self.storage.save_metadata(self.metadata)
                return SimulationRun(metadata=self.metadata, simulated_messages=[])
            
            self.metadata.start_trigger_found = True
            self.metadata.start_trigger_index = start_idx
            
            # Find end trigger
            end_idx, end_trigger_type = find_end_trigger(self.messages, start_idx)
            self.metadata.end_trigger_type = end_trigger_type
            
            # Group customer messages
            groups = group_customer_messages(
                self.messages,
                start_idx,
                end_idx,
                self.time_window_seconds
            )
            
            self.metadata.total_customer_groups = len(groups)
            
            # Save initial metadata
            self.storage.save_metadata(self.metadata)
            
            # Process each group
            for idx, group in enumerate(groups):
                self.metadata.current_group = idx + 1

                # Build context up to this group's last message
                context = self._build_context(group.last_message_index)

                # Generate response
                response_text = self._generate_response(context, group, agent=agent)
                
                # Create simulated message
                # Use the last message in the group as reference
                simulated_msg = self._create_simulated_message(
                    response_text,
                    group.messages[-1],
                    is_payment=False
                )
                
                self.simulated_messages.append(simulated_msg)
                self.metadata.total_simulated_responses += 1
                
                # Update metadata
                self.storage.save_metadata(self.metadata)
            
            # Mark as completed
            self.metadata.status = "completed"
            self.metadata.completed_at = datetime.now()
            self.metadata.duration_seconds = (
                self.metadata.completed_at - self.metadata.started_at
            ).total_seconds()
            
            # Save final results
            self.storage.save_metadata(self.metadata)
            self.storage.save_messages(
                self.chat_id,
                self.run_id,
                self.simulated_messages
            )
            
            return SimulationRun(
                metadata=self.metadata,
                simulated_messages=self.simulated_messages
            )
            
        except Exception as e:
            self.metadata.status = "failed"
            self.metadata.errors.append(str(e))
            self.metadata.completed_at = datetime.now()
            self.storage.save_metadata(self.metadata)
            raise
