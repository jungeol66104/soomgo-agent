"""Test script for central database functionality."""

import json
from pathlib import Path
from src.scraper.central_db import CentralChatDatabase
from src.models import ChatItem, QuoteInfo, UserInfo, ServiceInfo, RequestInfo, AddressInfo


def create_mock_chat(chat_id: int, updated_at: str = "2025-01-30T10:00:00Z") -> ChatItem:
    """Create a mock ChatItem for testing."""
    return ChatItem(
        id=chat_id,
        quote=QuoteInfo(
            id=chat_id * 10,
            price=100000,
            is_hired=False,
            is_instantmatch=False,
            is_extra_pro=False,
            unit="원",
            is_opened=True,
            is_reward=False
        ),
        user=UserInfo(
            id=chat_id * 100,
            address="서울 강남구",
            is_leaved=False,
            name=f"테스트유저{chat_id}",
            profile_image=None,
            is_certify_name=True,
            is_active=True,
            is_dormant=False,
            is_banned=False,
            is_soomgo_leaved=False
        ),
        service=ServiceInfo(title="영어과외"),
        request=RequestInfo(
            id=chat_id * 1000,
            is_targeted=False,
            object_id=f"obj_{chat_id}",
            address=AddressInfo(
                address1="서울",
                address2="강남구",
                address3="역삼동"
            )
        ),
        is_favorite=False,
        last_message_type="text",
        last_message=f"Test message {chat_id}",
        created_at="2025-01-20T10:00:00Z",
        updated_at=updated_at,
        escrow=None,
        new_message_count=0,
        unlock=True,
        unlock_customer=True,
        role="provider",
        is_induce_customer=False,
        safe_payment=None,
        provider_message_count=5,
        notification_status=True
    )


def test_central_database():
    """Test central database operations."""
    print("🧪 Testing Central Database Functionality\n")

    # Use a test database file
    test_db_path = "data/test_chat_list_master.jsonl"
    db = CentralChatDatabase(test_db_path)

    # Clean up any existing test file
    if Path(test_db_path).exists():
        Path(test_db_path).unlink()
        print("✓ Cleaned up existing test database\n")

    # Test 1: First run - Add 5 chats
    print("📝 Test 1: First Run (5 new chats)")
    print("-" * 50)
    run1_chats = [create_mock_chat(i) for i in range(1, 6)]

    existing = db.load()
    print(f"  Loaded existing chats: {len(existing)}")

    merged, new_count, updated_count = db.merge_and_update(existing, run1_chats)
    print(f"  Merged: {new_count} new, {updated_count} updated")

    db.save(merged)
    print(f"  ✓ Saved {len(merged)} chats to central database\n")

    assert len(merged) == 5, "Should have 5 chats after first run"
    assert new_count == 5, "Should have 5 new chats"
    assert updated_count == 0, "Should have 0 updated chats"

    # Test 2: Second run - 3 existing (updated) + 2 new
    print("📝 Test 2: Second Run (3 updated + 2 new)")
    print("-" * 50)
    run2_chats = [
        create_mock_chat(1, "2025-01-31T12:00:00Z"),  # Updated
        create_mock_chat(2, "2025-01-31T12:00:00Z"),  # Updated
        create_mock_chat(3, "2025-01-31T12:00:00Z"),  # Updated
        create_mock_chat(6),  # New
        create_mock_chat(7),  # New
    ]

    existing = db.load()
    print(f"  Loaded existing chats: {len(existing)}")

    merged, new_count, updated_count = db.merge_and_update(existing, run2_chats)
    print(f"  Merged: {new_count} new, {updated_count} updated")

    db.save(merged)
    print(f"  ✓ Saved {len(merged)} chats to central database\n")

    assert len(merged) == 7, "Should have 7 chats total"
    assert new_count == 2, "Should have 2 new chats"
    assert updated_count == 3, "Should have 3 updated chats"

    # Test 3: Verify data integrity
    print("📝 Test 3: Verify Data Integrity")
    print("-" * 50)
    loaded = db.load()
    print(f"  Loaded {len(loaded)} chats from database")

    # Check that updated chats have new timestamps
    chat_1 = loaded[1]
    assert chat_1.updated_at == "2025-01-31T12:00:00Z", "Chat 1 should be updated"
    print(f"  ✓ Chat 1 updated_at: {chat_1.updated_at}")

    # Check that new chats exist
    assert 6 in loaded, "Chat 6 should exist"
    assert 7 in loaded, "Chat 7 should exist"
    print(f"  ✓ New chats (6, 7) exist in database")

    # Check that old chat still exists
    assert 4 in loaded, "Chat 4 should still exist"
    print(f"  ✓ Old chat (4) still exists\n")

    # Test 4: Get stats
    print("📝 Test 4: Database Statistics")
    print("-" * 50)
    stats = db.get_stats()
    print(f"  Total chats: {stats['total_chats']}")
    print(f"  Oldest chat: {stats['oldest_chat']}")
    print(f"  Newest chat: {stats['newest_chat']}")
    print(f"  Unique services: {stats['unique_services']}\n")

    assert stats['total_chats'] == 7, "Should have 7 total chats"

    # Test 5: Verify file format (JSONL)
    print("📝 Test 5: Verify File Format")
    print("-" * 50)
    with open(test_db_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"  File has {len(lines)} lines")
    assert len(lines) == 7, "JSONL file should have 7 lines"

    # Parse first line to verify it's valid JSON
    first_chat = json.loads(lines[0])
    print(f"  First chat ID: {first_chat['id']}")
    print(f"  ✓ File format is valid JSONL\n")

    # Clean up
    print("🧹 Cleaning up test database...")
    Path(test_db_path).unlink()
    print("✓ Test database deleted\n")

    print("=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    test_central_database()
