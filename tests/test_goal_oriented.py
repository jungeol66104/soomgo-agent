#!/usr/bin/env python3
"""Test goal-oriented information gathering."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent import SoomgoAgent


def test_conversation():
    """Test a sample goal-oriented conversation."""
    print("=" * 80)
    print("TESTING GOAL-ORIENTED INFORMATION GATHERING")
    print("=" * 80)
    print()

    agent = SoomgoAgent()
    history = []
    gathered_info = None
    conversation_state = None
    last_closure_response = None

    # Simulate a conversation
    test_messages = [
        "안녕하세요 자소서 도움 받고 싶어요",
        "삼성전자 인사팀에 지원하려고 합니다",
        "마감은 다음주 금요일이에요. 경력은 3년차입니다",
        "초안은 있는데 방향성이 맞는지 잘 모르겠어요",
        "예산은 20만원 정도 생각하고 있습니다"
    ]

    for i, user_msg in enumerate(test_messages, 1):
        print(f"\n[Turn {i}]")
        print(f"User: {user_msg}")

        response, gathered_info, conversation_state, last_closure_response = agent.chat(
            user_msg, history, gathered_info, conversation_state, last_closure_response
        )

        print(f"Agent: {response}")
        print(f"State: {conversation_state}")
        print()
        print("Gathered Info:")
        for key, value in gathered_info.items():
            if value:
                print(f"  ✓ {key}: {value}")
            else:
                print(f"  ✗ {key}: (not yet)")

        # Update history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})

        print("-" * 80)

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    test_conversation()
