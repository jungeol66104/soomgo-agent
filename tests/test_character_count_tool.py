"""Test the character counting tool integration."""

import os
# Suppress debug logs for clean output
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.agent.core import SoomgoAgent

def test_character_count():
    """Test that the agent can accurately count characters using the tool."""
    agent = SoomgoAgent()

    # Test 1: Simple character count
    print("=" * 60)
    print("TEST 1: Simple character count")
    print("=" * 60)
    response, _, _, _ = agent.chat("안녕하세요 이 문장은 몇 글자인가요?")
    print(f"User: 안녕하세요 이 문장은 몇 글자인가요?")
    print(f"Agent: {response}")
    print()

    # Test 2: English text
    print("=" * 60)
    print("TEST 2: English text character count")
    print("=" * 60)
    response, _, _, _ = agent.chat("How many characters are in: Hello World")
    print(f"User: How many characters are in: Hello World")
    print(f"Agent: {response}")
    print()

    # Test 3: Count with and without spaces
    print("=" * 60)
    print("TEST 3: Count without spaces")
    print("=" * 60)
    response, _, _, _ = agent.chat("Count characters without spaces in: Hello World")
    print(f"User: Count characters without spaces in: Hello World")
    print(f"Agent: {response}")
    print()

    # Test 4: Long text
    print("=" * 60)
    print("TEST 4: Long text")
    print("=" * 60)
    long_text = "자기소개서 작성이 너무 어려워요. 어떻게 해야 하나요?"
    response, _, _, _ = agent.chat(f"이 문장의 글자수를 알려주세요: {long_text}")
    print(f"User: 이 문장의 글자수를 알려주세요: {long_text}")
    print(f"Agent: {response}")
    print()

if __name__ == "__main__":
    test_character_count()
