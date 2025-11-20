#!/usr/bin/env python3
"""Test handling of brief acknowledgment messages."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent import SoomgoAgent


def test_brief_acknowledgments():
    """Test that agent handles brief responses appropriately."""
    print("=" * 80)
    print("TESTING BRIEF ACKNOWLEDGMENT HANDLING")
    print("=" * 80)
    print()

    agent = SoomgoAgent()
    history = []
    gathered_info = None

    # Simulate the problematic conversation
    test_messages = [
        "아녀 근데 뭘 고쳐야할지 모르겠어서요. 냉정한 평가가 필요합니다.",
        "네 알겠습니다!",
        "네!",
    ]

    for i, user_msg in enumerate(test_messages, 1):
        print(f"\n[Turn {i}]")
        print(f"User ({len(user_msg)} chars): {user_msg}")

        response, gathered_info = agent.chat(user_msg, history, gathered_info)

        print(f"Agent ({len(response)} chars): {response}")

        # Update history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})

        # Check if response is appropriately brief for brief user messages
        if len(user_msg) < 10:  # Very brief user message
            if len(response) > 50:
                print(f"⚠️  WARNING: User message was {len(user_msg)} chars, but agent responded with {len(response)} chars (should be <50)")
            else:
                print(f"✓ Good: Agent kept response brief ({len(response)} chars)")

        print("-" * 80)

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    test_brief_acknowledgments()
