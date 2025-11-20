#!/usr/bin/env python3
"""
2-Stage Hybrid Pipeline for Finding Natural Conversations
Stage 1: Heuristic Filter (fast, free)
Stage 2: LLM Judge (accurate, affordable)

Key Feature: Filters out system messages and templates to analyze ONLY human conversation
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================================
# MESSAGE CLEANING: Remove Templates and System Messages
# ============================================================================

# Template patterns that indicate auto-generated service descriptions
TEMPLATE_PATTERNS = [
    "지난 시즌 합격률 80%",
    "[서비스 안내]",
    "라이트 패키지",
    "맞춤형 자소서/면접 패키지",
    "[합격 사례 및 강점]",
    "삼성엔지니어링, LG전자, YG엔터테인먼트",
    "먼저 1만원 맛보기 첨삭으로",
    "면접 원샷 마스터 코칭",
    "포트폴리오 제작 서비스 안내",
    "[핵심 면접 Q-Pack]",
    "포트폴리오 기획 (스토리 설계)",
]

# System message types to always filter out
SYSTEM_MESSAGE_TYPES = {
    'ST_QUOTE',     # Welcome message
    'ST_002',       # Cache refund notification
    'ST_003',       # Quote viewed notification
    'SP_ST_002',    # Soomgo Pay recommendation
    'SP_SB_001',    # System notifications
    'SB_005',       # System notifications
    'SB_001',       # System notifications
    'RQ_001',       # Request context (not conversation)
}


def is_template_message(message: str) -> bool:
    """Check if message is a system-generated template."""
    if not message or len(message) < 50:
        return False

    # Long messages with template keywords are likely templates
    if len(message) > 400:
        for pattern in TEMPLATE_PATTERNS:
            if pattern in message:
                return True

    return False


def is_file_upload_message(message: str) -> bool:
    """Check if message is just a file upload notification."""
    return message.strip() == "사진을 보냈습니다." or message.strip() == "파일을 보냈습니다."


def clean_messages(messages: List[Dict]) -> List[Dict]:
    """
    Filter out system messages, templates, and file uploads.
    Returns only real human conversation messages.
    """
    cleaned = []

    for msg in messages:
        # Skip if no message content
        if not msg.get('message'):
            continue

        # Skip system message types
        if msg.get('type') in SYSTEM_MESSAGE_TYPES:
            continue

        # Skip system user (id=0)
        if msg['user']['id'] == 0:
            continue

        # Skip template messages
        if is_template_message(msg['message']):
            continue

        # Skip file upload notifications
        if is_file_upload_message(msg['message']):
            continue

        cleaned.append(msg)

    return cleaned


# ============================================================================
# STAGE 1: HEURISTIC FILTER
# ============================================================================

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


def heuristic_filter(messages: List[Dict]) -> bool:
    """
    Stage 1: Fast heuristic filter on CLEANED messages.
    Returns True if conversation is a candidate for Stage 2.
    """
    # First, clean the messages (remove templates and system messages)
    clean = clean_messages(messages)

    # Must have at least 3 real human messages
    if len(clean) < 3:
        return False

    # Must have at least 2 different people
    user_ids = [m['user']['id'] for m in clean]
    if len(set(user_ids)) < 2:
        return False

    # Check for back-and-forth (not all from same user)
    first_user = user_ids[0]
    if user_ids.count(first_user) > len(user_ids) * 0.8:  # One user dominates >80%
        return False

    # Total conversation length after cleaning
    total_chars = sum(len(m['message']) for m in clean)
    if total_chars < 50 or total_chars > 2000:
        return False

    # At least one message should be substantial (10-300 chars)
    substantial = [m for m in clean if 10 <= len(m['message']) <= 300]
    if len(substantial) < 2:
        return False

    return True


def run_stage1(data_dir: Path, max_candidates: int = 500) -> List[Tuple[Path, List[Dict]]]:
    """
    Stage 1: Run heuristic filter on all conversations.
    Returns list of (file_path, messages) tuples.
    """
    messages_dir = data_dir / 'messages'
    chat_files = list(messages_dir.glob('chat_*.jsonl'))

    print(f"🔍 Stage 1: Heuristic Filter")
    print(f"   Total conversations: {len(chat_files)}")

    candidates = []

    for i, chat_file in enumerate(chat_files):
        if i % 500 == 0:
            print(f"   Processed: {i}/{len(chat_files)}...")

        messages = load_conversation(chat_file)

        if heuristic_filter(messages):
            candidates.append((chat_file, messages))

            if len(candidates) >= max_candidates:
                break

    print(f"   ✓ Filtered to {len(candidates)} candidates")
    return candidates


# ============================================================================
# STAGE 2: LLM JUDGE
# ============================================================================

def format_conversation_for_llm(messages: List[Dict]) -> str:
    """
    Format conversation for LLM evaluation.
    ONLY includes cleaned human messages (no templates, no system messages).
    """
    # Clean messages first
    clean = clean_messages(messages)

    # Track users
    user_map = {}
    lines = []

    for msg in clean:
        user_id = msg['user']['id']
        if user_id not in user_map:
            user_map[user_id] = f"Person{len(user_map)+1}"

        user_label = user_map[user_id]
        text = msg['message']
        lines.append(f"{user_label}: {text}")

    return '\n'.join(lines)


def llm_score_conversation(conversation_text: str) -> Tuple[float, str]:
    """
    Stage 2: Use LLM to score conversation naturalness.
    Returns (score, reasoning).
    """

    prompt = f"""당신은 대화의 자연스러움을 평가하는 전문가입니다.

다음 대화를 읽고 **1~10점** 사이의 점수를 매겨주세요.

**평가 기준:**
- 자연스러운 한국어 표현 (formal vs casual 적절성)
- 맥락과 흐름이 자연스러운가
- 실제 사람같은 톤인가, 아니면 로봇/템플릿 같은가
- 감정과 공감이 느껴지는가
- 과도한 존댓말, 이모티콘, 반복적 패턴이 있는가

**점수 기준:**
- 1-3점: 매우 부자연스러움 (로봇 같음, 템플릿)
- 4-6점: 보통 (약간 어색하지만 대화는 됨)
- 7-9점: 자연스러움 (실제 사람 같음)
- 10점: 완벽함 (매우 자연스럽고 인간적)

**대화:**
{conversation_text}

**출력 형식 (반드시 JSON으로):**
{{
  "score": <1~10 사이 숫자>,
  "reasoning": "<한 줄 평가 이유>"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert at evaluating conversation naturalness. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result['score'], result['reasoning']

    except Exception as e:
        print(f"   ⚠️  LLM error: {e}")
        return 0.0, "Error in scoring"


def run_stage2(candidates: List[Tuple[Path, List[Dict]]], top_n: int = 10) -> List[Dict]:
    """
    Stage 2: Score candidates with LLM and return top N.
    """
    print(f"\n🤖 Stage 2: LLM Judge")
    print(f"   Scoring {len(candidates)} candidates...")

    results = []

    for i, (chat_file, messages) in enumerate(candidates):
        if i % 50 == 0:
            print(f"   Scored: {i}/{len(candidates)}...")

        # Get cleaned conversation text for LLM
        conversation_text = format_conversation_for_llm(messages)

        # Skip if cleaned conversation is too short
        if len(conversation_text) < 20:
            continue

        score, reasoning = llm_score_conversation(conversation_text)

        # Count messages before and after cleaning
        clean_count = len(clean_messages(messages))
        raw_count = len([m for m in messages if m.get('message')])

        results.append({
            'file': chat_file.name,
            'score': score,
            'reasoning': reasoning,
            'conversation': conversation_text,
            'raw_messages': messages,
            'clean_count': clean_count,
            'raw_count': raw_count,
        })

    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)

    if results:
        print(f"   ✓ Top score: {results[0]['score']}")
        print(f"   ✓ Median score: {results[len(results)//2]['score']}")

    return results[:top_n]


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run the full 2-stage pipeline."""

    print("="*80)
    print("FINDING MOST NATURAL CONVERSATIONS")
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

    # Stage 1: Heuristic filter
    candidates = run_stage1(data_dir, max_candidates=500)

    if not candidates:
        print("❌ No candidates found after Stage 1")
        return

    # Stage 2: LLM scoring
    top_10 = run_stage2(candidates, top_n=10)

    # Display results
    print("\n" + "="*80)
    print("TOP 10 MOST NATURAL CONVERSATIONS")
    print("="*80)

    for i, result in enumerate(top_10, 1):
        print(f"\n[{i}] Score: {result['score']}/10 | {result['file']}")
        print(f"Messages: {result['raw_count']} raw → {result['clean_count']} cleaned")
        print(f"Reasoning: {result['reasoning']}")
        print("-" * 80)
        print(result['conversation'])
        print()

    # Save results to data/analysis/
    output_dir = Path('data/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_json = output_dir / 'best_conversations.json'
    output_txt = output_dir / 'best_conversations.txt'

    # Save JSON (for programmatic use)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(top_10, f, ensure_ascii=False, indent=2)

    # Save TXT (for human reading)
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write("TOP 10 MOST NATURAL CONVERSATIONS\n")
        f.write("(Templates and system messages filtered out)\n")
        f.write("="*80 + "\n\n")

        for i, result in enumerate(top_10, 1):
            f.write(f"[{i}] Score: {result['score']}/10 | {result['file']}\n")
            f.write(f"Messages: {result['raw_count']} raw → {result['clean_count']} cleaned\n")
            f.write(f"Reasoning: {result['reasoning']}\n")
            f.write("-"*80 + "\n")
            f.write(result['conversation'] + "\n")
            f.write("\n\n")

    print(f"✅ Results saved:")
    print(f"   - {output_json} (JSON)")
    print(f"   - {output_txt} (Text)")


if __name__ == '__main__':
    main()
