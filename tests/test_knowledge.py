#!/usr/bin/env python3
"""Test knowledge-grounded responses."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent import SoomgoAgent


def test_knowledge():
    """Test that agent answers questions using knowledge base."""
    print("=" * 80)
    print("TESTING KNOWLEDGE-GROUNDED RESPONSES")
    print("=" * 80)
    print()

    agent = SoomgoAgent()
    history = []
    gathered_info = None
    conversation_state = None
    last_closure_response = None

    # Test queries that should retrieve knowledge
    test_messages = [
        "자기소개서 가격이 얼마예요?",
        "비용이 좀 부담되는데 어떻게 할 수 있을까요?",
        "급하게 할 수 있나요?",
        "환불 가능한가요?",
    ]

    for i, user_msg in enumerate(test_messages, 1):
        print(f"\n{'='*80}")
        print(f"[Test {i}] User: {user_msg}")
        print('='*80)

        response, gathered_info, conversation_state, last_closure_response = agent.chat(
            user_msg, history, gathered_info, conversation_state, last_closure_response
        )

        print(f"Agent: {response}")
        print()

        # Check if response contains relevant information
        checks = []
        if i == 1:  # 자기소개서 가격
            checks = ["100자", "6,000원", "4,000원"]
        elif i == 2:  # 비용 부담
            checks = ["예산", "조정"]
        elif i == 3:  # 급행
            checks = ["급행", "50,000원", "24시간"]
        elif i == 4:  # 환불
            checks = ["환불", "100%", "착수"]

        found = [check for check in checks if check in response]
        print(f"✓ Information check: {len(found)}/{len(checks)} keywords found")
        if found:
            print(f"  Found: {', '.join(found)}")

        # Update history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})

        print("-" * 80)

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    test_knowledge()
