#!/usr/bin/env python3
"""Test pricing with conversation context."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent import SoomgoAgent


def test_context_pricing():
    """Test that agent uses context to answer pricing questions."""
    print("=" * 80)
    print("TESTING CONTEXT-AWARE PRICING")
    print("=" * 80)
    print()

    agent = SoomgoAgent()
    history = []
    gathered_info = None
    conversation_state = None
    last_closure_response = None

    test_messages = [
        "자소서 쓰고싶은데 가능할까요",
        "얼마인가요?",
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

        # Check gathered info
        if gathered_info:
            print(f"Gathered info: service_type = {gathered_info.get('service_type')}")

        # Check if pricing is mentioned
        if i == 2:  # "얼마인가요?"
            if any(price in response for price in ["100자당", "6,000원", "4,000원"]):
                print("✅ SUCCESS: Agent provided pricing!")
            else:
                print("❌ FAIL: Agent did NOT provide pricing")
                print(f"   Response: {response[:100]}")

        # Update history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})

        print("-" * 80)

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    test_context_pricing()
