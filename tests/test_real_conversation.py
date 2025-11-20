#!/usr/bin/env python3
"""Test the exact conversation from user."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent import SoomgoAgent


def test_real_conversation():
    """Test exact conversation that showed wrong pricing."""
    print("=" * 80)
    print("TESTING REAL CONVERSATION")
    print("=" * 80)
    print()

    agent = SoomgoAgent()
    history = []
    gathered_info = None
    conversation_state = None
    last_closure_response = None

    test_messages = [
        "안녕하세요!",
        "혹시 어떤 서비스 제공하시는지 알 수 있을까요?",
        "가격도 함께 말씀 부탁드립니다!",
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

        # Check for wrong information
        if "문항당" in response:
            print("❌ ERROR: Agent said '문항당' but should be '100자당'")
        if "2만원" in response and "자소서" in response:
            print("❌ ERROR: Wrong pricing for 자소서 첨삭 (should be 100자당 4,000원)")
        if "면접 준비: 5만원" in response:
            print("❌ ERROR: No such service as '면접 준비 5만원 1시간'")
        if "10만원부터" in response and "포트폴리오" in response:
            print("❌ ERROR: Wrong portfolio pricing")

        # Check for correct information
        if "100자당" in response and "4,000원" in response:
            print("✓ Correct: 자소서 첨삭 100자당 4,000원")
        if "100자당" in response and "6,000원" in response:
            print("✓ Correct: 자소서 신규 100자당 6,000원")
        if "30,000원" in response and "이력서" in response:
            print("✓ Correct: 이력서 30,000원")

        # Update history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})

        print("-" * 80)

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    test_real_conversation()
