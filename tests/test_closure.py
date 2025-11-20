#!/usr/bin/env python3
"""Test conversation closure handling."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent import SoomgoAgent


def test_closure():
    """Test that agent properly handles conversation closure."""
    print("=" * 80)
    print("TESTING CONVERSATION CLOSURE HANDLING")
    print("=" * 80)
    print()

    agent = SoomgoAgent()
    history = []
    gathered_info = None
    conversation_state = None
    last_closure_response = None

    # Simulate the problematic conversation
    test_messages = [
        "알겠습니다! 고려해보고 다시 말씀드릴게요!",
        "네!",
        "네!",
    ]

    for i, user_msg in enumerate(test_messages, 1):
        print(f"\n[Turn {i}]")
        print(f"User ({len(user_msg)} chars): {user_msg}")

        response, gathered_info, conversation_state, last_closure_response = agent.chat(
            user_msg, history, gathered_info, conversation_state, last_closure_response
        )

        print(f"Agent ({len(response)} chars): {response}")
        print(f"Conversation State: {conversation_state}")
        if last_closure_response:
            print(f"Last Closure: {last_closure_response[:50]}...")

        # Update history
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": response})

        # Check for issues
        if i == 1:  # First "고려해보고" message
            if conversation_state != "deferred":
                print(f"⚠️  WARNING: Expected state 'deferred', got '{conversation_state}'")
            else:
                print(f"✓ Correctly detected deferred state")

        elif i >= 2:  # Subsequent "네!" messages
            if conversation_state != "closed":
                print(f"⚠️  WARNING: Expected state 'closed', got '{conversation_state}'")
            else:
                print(f"✓ Correctly detected closed state")

            if len(response) > 30:
                print(f"⚠️  WARNING: Response too long ({len(response)} chars) for closed conversation")
            else:
                print(f"✓ Response appropriately brief")

            # Check for repeated closure phrases
            if i > 2 and any(phrase in response for phrase in ["기다릴게요", "편하실 때", "연락 주세요", "언제든지"]):
                print(f"⚠️  WARNING: Repeated closure phrases detected")
            else:
                print(f"✓ No repeated closure phrases")

        print("-" * 80)

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print()
    print("Summary:")
    print(f"  Final state: {conversation_state}")
    print(f"  Last closure: {last_closure_response[:50] if last_closure_response else 'None'}...")
    print("=" * 80)


if __name__ == '__main__':
    test_closure()
