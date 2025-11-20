#!/usr/bin/env python3
"""
Exploratory Analysis of Soomgo Conversations
- Sample random conversations
- Generate statistics
- Output for analysis
"""

import json
import random
from pathlib import Path
from typing import List, Dict
from collections import Counter, defaultdict

def load_conversation(chat_file: Path) -> List[Dict]:
    """Load messages from a chat file."""
    messages = []
    with open(chat_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError:
                continue
    return messages


def analyze_message_types(all_messages: List[List[Dict]]) -> Dict:
    """Analyze distribution of message types."""
    type_counter = Counter()
    own_type_counter = Counter()

    for messages in all_messages:
        for msg in messages:
            type_counter[msg.get('type', 'UNKNOWN')] += 1
            if msg.get('own_type'):
                own_type_counter[msg['own_type']] += 1

    return {
        'type': dict(type_counter),
        'own_type': dict(own_type_counter)
    }


def analyze_message_lengths(all_messages: List[List[Dict]]) -> Dict:
    """Analyze message length distribution."""
    lengths = []

    for messages in all_messages:
        for msg in messages:
            if msg.get('message'):
                lengths.append(len(msg['message']))

    if not lengths:
        return {}

    lengths.sort()
    return {
        'min': lengths[0],
        'max': lengths[-1],
        'median': lengths[len(lengths)//2],
        'mean': sum(lengths) / len(lengths),
        'p25': lengths[len(lengths)//4],
        'p75': lengths[3*len(lengths)//4],
        'total_messages': len(lengths)
    }


def analyze_conversation_structure(all_messages: List[List[Dict]]) -> Dict:
    """Analyze conversation structure patterns."""
    exchange_counts = []
    user_counts = []

    for messages in all_messages:
        # Count messages with actual text
        text_messages = [m for m in messages if m.get('message')]
        exchange_counts.append(len(text_messages))

        # Count unique users
        user_ids = set(m['user']['id'] for m in messages if m['user']['id'] != 0)
        user_counts.append(len(user_ids))

    if not exchange_counts:
        return {}

    exchange_counts.sort()
    return {
        'exchanges': {
            'min': min(exchange_counts),
            'max': max(exchange_counts),
            'median': exchange_counts[len(exchange_counts)//2],
            'mean': sum(exchange_counts) / len(exchange_counts)
        },
        'unique_users': {
            'min': min(user_counts),
            'max': max(user_counts),
            'median': user_counts[len(user_counts)//2],
            'mean': sum(user_counts) / len(user_counts)
        }
    }


def format_conversation(messages: List[Dict], show_metadata: bool = True) -> str:
    """Format a conversation for display."""
    lines = []

    # Track users
    user_map = {}

    for i, msg in enumerate(messages, 1):
        user_id = msg['user']['id']

        # Map user IDs to readable names
        if user_id == 0:
            user_label = "SYSTEM"
        else:
            if user_id not in user_map:
                user_map[user_id] = f"User{len(user_map)+1}"
            user_label = user_map[user_id]

        text = msg.get('message', '[NO TEXT]')
        msg_type = msg.get('type', 'UNKNOWN')

        if show_metadata:
            lines.append(f"[{i}] {user_label} ({msg_type}): {text}")
        else:
            lines.append(f"{user_label}: {text}")

    return '\n'.join(lines)


def main():
    """Run exploratory analysis."""

    print("="*80)
    print("EXPLORATORY CONVERSATION ANALYSIS")
    print("="*80)

    # Find latest export
    export_dir = Path('export')
    exports = sorted(export_dir.glob('*_export'))

    if not exports:
        print("❌ No exports found!")
        return

    latest_export = exports[-1]
    print(f"📁 Using export: {latest_export.name}\n")

    data_dir = latest_export / 'data'
    messages_dir = data_dir / 'messages'

    # Get all chat files
    chat_files = list(messages_dir.glob('chat_*.jsonl'))
    print(f"📊 Total conversations: {len(chat_files)}\n")

    # Sample conversations
    print("📥 Loading sample conversations...")
    sample_size = min(100, len(chat_files))  # Load 100 for stats
    sample_files = random.sample(chat_files, sample_size)

    all_messages = []
    for chat_file in sample_files:
        messages = load_conversation(chat_file)
        all_messages.append(messages)

    print(f"✓ Loaded {len(all_messages)} conversations\n")

    # Generate statistics
    print("📈 Generating statistics...")

    type_stats = analyze_message_types(all_messages)
    length_stats = analyze_message_lengths(all_messages)
    structure_stats = analyze_conversation_structure(all_messages)

    # Select 30 diverse conversations for detailed review
    print("📋 Selecting diverse sample conversations...\n")

    # Sort by length to get diversity
    sorted_by_length = sorted(
        zip(sample_files, all_messages),
        key=lambda x: len(x[1])
    )

    # Pick from different quartiles
    display_count = 30
    step = len(sorted_by_length) // display_count
    diverse_sample = [sorted_by_length[i*step] for i in range(display_count)]

    # Write output to data/analysis/
    output_dir = Path('data/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'exploratory_analysis.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("SOOMGO CONVERSATION EXPLORATORY ANALYSIS\n")
        f.write("="*80 + "\n\n")

        # 1. Overview
        f.write("## 1. DATASET OVERVIEW\n")
        f.write("-"*80 + "\n")
        f.write(f"Total conversations in dataset: {len(chat_files)}\n")
        f.write(f"Sample analyzed: {len(all_messages)}\n")
        f.write(f"Conversations displayed below: {len(diverse_sample)}\n\n")

        # 2. Message Type Distribution
        f.write("## 2. MESSAGE TYPE DISTRIBUTION\n")
        f.write("-"*80 + "\n")
        f.write("Main types:\n")
        for msg_type, count in sorted(type_stats['type'].items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {msg_type}: {count}\n")
        f.write("\nOwn types:\n")
        for own_type, count in sorted(type_stats['own_type'].items(), key=lambda x: x[1], reverse=True)[:10]:
            f.write(f"  {own_type}: {count}\n")
        f.write("\n")

        # 3. Message Length Stats
        f.write("## 3. MESSAGE LENGTH STATISTICS\n")
        f.write("-"*80 + "\n")
        f.write(f"Total messages with text: {length_stats['total_messages']}\n")
        f.write(f"Min length: {length_stats['min']} chars\n")
        f.write(f"Max length: {length_stats['max']} chars\n")
        f.write(f"Mean length: {length_stats['mean']:.1f} chars\n")
        f.write(f"Median length: {length_stats['median']} chars\n")
        f.write(f"25th percentile: {length_stats['p25']} chars\n")
        f.write(f"75th percentile: {length_stats['p75']} chars\n\n")

        # 4. Conversation Structure
        f.write("## 4. CONVERSATION STRUCTURE\n")
        f.write("-"*80 + "\n")
        f.write("Exchanges per conversation:\n")
        f.write(f"  Min: {structure_stats['exchanges']['min']}\n")
        f.write(f"  Max: {structure_stats['exchanges']['max']}\n")
        f.write(f"  Mean: {structure_stats['exchanges']['mean']:.1f}\n")
        f.write(f"  Median: {structure_stats['exchanges']['median']}\n")
        f.write("\nUnique users per conversation:\n")
        f.write(f"  Min: {structure_stats['unique_users']['min']}\n")
        f.write(f"  Max: {structure_stats['unique_users']['max']}\n")
        f.write(f"  Mean: {structure_stats['unique_users']['mean']:.1f}\n")
        f.write(f"  Median: {structure_stats['unique_users']['median']}\n\n")

        # 5. Sample Conversations
        f.write("## 5. SAMPLE CONVERSATIONS (30 DIVERSE EXAMPLES)\n")
        f.write("-"*80 + "\n\n")

        for i, (chat_file, messages) in enumerate(diverse_sample, 1):
            f.write(f"### CONVERSATION {i}\n")
            f.write(f"File: {chat_file.name}\n")
            f.write(f"Total messages: {len(messages)}\n")

            # Count text messages
            text_messages = [m for m in messages if m.get('message')]
            f.write(f"Messages with text: {len(text_messages)}\n")

            # Count unique users
            user_ids = set(m['user']['id'] for m in messages if m['user']['id'] != 0)
            f.write(f"Unique users: {len(user_ids)}\n")

            f.write("-"*80 + "\n")
            f.write(format_conversation(messages, show_metadata=True))
            f.write("\n\n" + "="*80 + "\n\n")

    print(f"✅ Analysis complete!")
    print(f"📄 Output saved to: {output_file}")
    print(f"\nNext steps:")
    print(f"  1. Review the statistics and sample conversations")
    print(f"  2. Identify patterns in natural vs robotic conversations")
    print(f"  3. Design heuristics based on findings")


if __name__ == '__main__':
    main()
