#!/usr/bin/env python3
"""Test exact user scenario."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent import SoomgoAgent


def test_user_scenario():
    """Test the exact conversation from user."""
    print("=" * 80)
    print("TESTING USER'S EXACT SCENARIO")
    print("=" * 80)
    print()

    agent = SoomgoAgent()
    history = []
    gathered_info = None
    conversation_state = None
    last_closure_response = None

    test_messages = [
        "안녕하세요!",
        "자소서 쓰고싶은데 가능할까요",
        "얼마인가요?",
        "책정된 가격이 없는건가요?",
    ]

    for i, user_msg in enumerate(test_messages, 1):
        print(f"\n{'='*80}")
        print(f"You: {user_msg}")
        print('='*80)

        response, gathered_info, conversation_state, last_closure_response = agent.chat(
            user_msg, history, gathered_info, conversation_state, last_closure_response
        )

        print(f"Agent: {response}")
        print()

        # Update history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})

        print("-" * 80)

    print()
    print("=" * 80)
    print("✅ Agent should have provided pricing for 자소서")
    print("=" * 80)


if __name__ == '__main__':
    test_user_scenario()
