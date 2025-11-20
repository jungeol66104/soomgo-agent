"""Create a timestamped export package for sharing data with colleagues."""

import json
import csv
import shutil
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any

# Source paths
DATA_DIR = Path("data")
CHAT_LIST_FILE = DATA_DIR / "chat_list_master.jsonl"
MESSAGES_DIR = DATA_DIR / "messages"
MODELS_FILE = Path("src/models.py")

# Export root
EXPORT_ROOT = Path("export")


def create_export_directory() -> Path:
    """Create timestamped export directory."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    export_dir = EXPORT_ROOT / f"{timestamp}_export"

    # Create directory structure
    (export_dir / "data" / "messages").mkdir(parents=True, exist_ok=True)
    (export_dir / "analysis").mkdir(parents=True, exist_ok=True)

    return export_dir


def load_chat_list() -> List[Dict[str, Any]]:
    """Load all chats from master list."""
    chats = []
    with open(CHAT_LIST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                chats.append(json.loads(line))
    return chats


def get_scraped_message_files() -> set:
    """Get all scraped message file IDs."""
    return set(f.stem.replace('chat_', '') for f in MESSAGES_DIR.glob('chat_*.jsonl'))


def analyze_message_stats(messages_dir: Path) -> Dict[str, Any]:
    """Analyze message statistics from scraped files."""
    stats = {
        'total_messages': 0,
        'total_conversations': 0,
        'messages_per_chat': [],
        'total_chars': 0,
        'messages_with_content': 0
    }

    for msg_file in messages_dir.glob('chat_*.jsonl'):
        message_count = 0
        chars_in_chat = 0

        with open(msg_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    message_count += 1
                    stats['total_messages'] += 1

                    msg = json.loads(line)
                    if msg.get('message'):
                        msg_len = len(msg['message'])
                        chars_in_chat += msg_len
                        stats['total_chars'] += msg_len
                        stats['messages_with_content'] += 1

        stats['total_conversations'] += 1
        stats['messages_per_chat'].append(message_count)

    # Calculate averages
    if stats['messages_per_chat']:
        stats['avg_messages_per_chat'] = round(sum(stats['messages_per_chat']) / len(stats['messages_per_chat']), 2)
        stats['min_messages_per_chat'] = min(stats['messages_per_chat'])
        stats['max_messages_per_chat'] = max(stats['messages_per_chat'])
    else:
        stats['avg_messages_per_chat'] = 0
        stats['min_messages_per_chat'] = 0
        stats['max_messages_per_chat'] = 0

    if stats['messages_with_content'] > 0:
        stats['avg_message_length'] = round(stats['total_chars'] / stats['messages_with_content'], 2)
    else:
        stats['avg_message_length'] = 0

    # Remove the raw list to keep JSON clean
    del stats['messages_per_chat']

    return stats


def analyze_completeness(chats: List[Dict], scraped_ids: set) -> Dict[str, Any]:
    """Analyze data completeness."""
    total_chats = len(chats)
    scraped_count = 0
    missing_chats = []

    for chat in chats:
        chat_id = str(chat['id'])
        if chat_id in scraped_ids:
            scraped_count += 1
        else:
            missing_chats.append({
                'id': chat['id'],
                'service': chat['service']['title'],
                'user_name': chat['user']['name'],
                'created_at': chat['created_at'],
                'updated_at': chat['updated_at']
            })

    completion_rate = round((scraped_count / total_chats * 100), 2) if total_chats > 0 else 0

    return {
        'total_chats': total_chats,
        'scraped_count': scraped_count,
        'missing_count': len(missing_chats),
        'completion_rate': completion_rate,
        'missing_chats': missing_chats
    }


def analyze_services(chats: List[Dict]) -> Dict[str, Any]:
    """Analyze service distribution."""
    services = Counter(chat['service']['title'] for chat in chats)
    total = len(chats)

    distribution = [
        {
            'service': service,
            'count': count,
            'percentage': round((count / total * 100), 2)
        }
        for service, count in services.most_common()
    ]

    return {
        'total_unique': len(services),
        'distribution': distribution
    }


def analyze_hiring(chats: List[Dict]) -> Dict[str, Any]:
    """Analyze hiring statistics."""
    hired = sum(1 for chat in chats if chat['quote']['is_hired'])
    not_hired = len(chats) - hired

    return {
        'hired_count': hired,
        'not_hired_count': not_hired,
        'hiring_rate': round((hired / len(chats) * 100), 2) if chats else 0
    }


def analyze_prices(chats: List[Dict]) -> Dict[str, Any]:
    """Analyze price statistics."""
    prices = [chat['quote']['price'] for chat in chats if chat['quote']['price'] > 0]

    if not prices:
        return {
            'min': 0,
            'max': 0,
            'avg': 0,
            'median': 0
        }

    sorted_prices = sorted(prices)
    median_idx = len(sorted_prices) // 2
    median = sorted_prices[median_idx] if len(sorted_prices) % 2 == 1 else (sorted_prices[median_idx - 1] + sorted_prices[median_idx]) / 2

    return {
        'min': min(prices),
        'max': max(prices),
        'avg': round(sum(prices) / len(prices), 2),
        'median': round(median, 2)
    }


def analyze_users(chats: List[Dict]) -> Dict[str, Any]:
    """Analyze user statistics."""
    total = len(chats)
    left = sum(1 for chat in chats if chat['user']['is_leaved'])
    banned = sum(1 for chat in chats if chat['user']['is_banned'])
    dormant = sum(1 for chat in chats if chat['user']['is_dormant'])

    return {
        'left_users': left,
        'left_percentage': round((left / total * 100), 2),
        'banned_users': banned,
        'banned_percentage': round((banned / total * 100), 2),
        'dormant_users': dormant,
        'dormant_percentage': round((dormant / total * 100), 2)
    }


def analyze_temporal(chats: List[Dict]) -> Dict[str, Any]:
    """Analyze temporal statistics."""
    if not chats:
        return {
            'created_at_range': {'oldest': None, 'newest': None},
            'updated_at_range': {'oldest': None, 'newest': None},
            'date_range_span_days': None
        }

    created_dates = [chat['created_at'] for chat in chats]
    updated_dates = [chat['updated_at'] for chat in chats]

    # Calculate span for updated_at (to verify filtering)
    from datetime import datetime
    oldest_update = datetime.fromisoformat(min(updated_dates))
    newest_update = datetime.fromisoformat(max(updated_dates))
    updated_span_days = (newest_update - oldest_update).days

    return {
        'created_at_range': {
            'oldest': min(created_dates),
            'newest': max(created_dates)
        },
        'updated_at_range': {
            'oldest': min(updated_dates),
            'newest': max(updated_dates)
        },
        'updated_at_span_days': updated_span_days
    }


def generate_data_summary(chats: List[Dict], completeness: Dict, message_stats: Dict) -> Dict[str, Any]:
    """Generate high-level summary."""
    services = analyze_services(chats)
    hiring = analyze_hiring(chats)
    temporal = analyze_temporal(chats)

    return {
        'generated_at': datetime.now().isoformat(),
        'dataset_info': {
            'total_chats': completeness['total_chats'],
            'messages_scraped': completeness['scraped_count'],
            'completion_rate': completeness['completion_rate'],
            'missing_count': completeness['missing_count']
        },
        'filter_info': {
            'description': 'Chats filtered by updated_at (last activity)',
            'updated_at_range': f"{temporal['updated_at_range']['oldest']} to {temporal['updated_at_range']['newest']}" if temporal['updated_at_range']['oldest'] else None,
            'updated_at_span_days': temporal['updated_at_span_days']
        },
        'top_insights': {
            'most_common_service': services['distribution'][0]['service'] if services['distribution'] else None,
            'hiring_rate': hiring['hiring_rate'],
            'created_at_range': f"{temporal['created_at_range']['oldest']} to {temporal['created_at_range']['newest']}" if temporal['created_at_range']['oldest'] else None,
            'total_messages': message_stats['total_messages'],
            'avg_messages_per_chat': message_stats['avg_messages_per_chat']
        }
    }


def generate_data_overview(chats: List[Dict], completeness: Dict, message_stats: Dict) -> Dict[str, Any]:
    """Generate detailed overview."""
    return {
        'generated_at': datetime.now().isoformat(),
        'completeness': completeness,
        'services': analyze_services(chats),
        'hiring_stats': analyze_hiring(chats),
        'price_stats': analyze_prices(chats),
        'user_stats': analyze_users(chats),
        'temporal_stats': analyze_temporal(chats),
        'message_stats': message_stats
    }


def save_csv_exports(export_dir: Path, chats: List[Dict], completeness: Dict):
    """Generate CSV files for Excel analysis."""
    analysis_dir = export_dir / "analysis"

    # 1. Services breakdown CSV
    services = analyze_services(chats)
    with open(analysis_dir / "services_breakdown.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['service', 'count', 'percentage'])
        writer.writeheader()
        writer.writerows(services['distribution'])

    # 2. Missing chats CSV
    if completeness['missing_chats']:
        with open(analysis_dir / "missing_chats.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'service', 'user_name', 'created_at', 'updated_at'])
            writer.writeheader()
            writer.writerows(completeness['missing_chats'])

    # 3. Full chat list export CSV (flattened)
    with open(analysis_dir / "chat_list_export.csv", 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'chat_id', 'service', 'user_name', 'user_address', 'price', 'is_hired',
            'created_at', 'updated_at', 'is_favorite', 'new_message_count',
            'provider_message_count', 'user_is_leaved', 'user_is_banned', 'user_is_dormant'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for chat in chats:
            writer.writerow({
                'chat_id': chat['id'],
                'service': chat['service']['title'],
                'user_name': chat['user']['name'],
                'user_address': chat['user']['address'],
                'price': chat['quote']['price'],
                'is_hired': chat['quote']['is_hired'],
                'created_at': chat['created_at'],
                'updated_at': chat['updated_at'],
                'is_favorite': chat['is_favorite'],
                'new_message_count': chat['new_message_count'],
                'provider_message_count': chat['provider_message_count'],
                'user_is_leaved': chat['user']['is_leaved'],
                'user_is_banned': chat['user']['is_banned'],
                'user_is_dormant': chat['user']['is_dormant']
            })


def create_readme(export_dir: Path, summary: Dict):
    """Create README for the export package."""
    readme_content = f"""# VF-Data 데이터 패키지

**생성 일시:** {summary['generated_at']}

## 데이터셋 개요

- **전체 채팅 수:** {summary['dataset_info']['total_chats']}
- **메시지 수집 완료:** {summary['dataset_info']['messages_scraped']}
- **수집 완료율:** {summary['dataset_info']['completion_rate']}%
- **가장 많은 서비스:** {summary['top_insights']['most_common_service']}
- **계약 성사율:** {summary['top_insights']['hiring_rate']}%
- **전체 메시지 수:** {summary['top_insights']['total_messages']}

## 날짜 범위

**중요:** 이 데이터셋은 최근 활동 날짜를 기준으로 필터링되었습니다.

- **생성 날짜 범위:** {summary['top_insights']['created_at_range']}
  - 채팅이 처음 생성된 기간
- **업데이트 날짜 범위 (필터 기준):** {summary['filter_info']['updated_at_range']} ({summary['filter_info']['updated_at_span_days']}일)
  - 이 기간에 활동이 있었던 채팅만 포함됨

## 포함된 파일

### 데이터 파일
- `data/chat_list_master.jsonl` - 전체 채팅 목록 (한 줄에 하나씩)
- `data/messages/` - 각 채팅의 메시지 파일들 (`chat_<id>.jsonl`)

### 분석 파일
- `analysis/data_summary.json` - 핵심 요약 통계
- `analysis/data_overview.json` - 상세 통계 분석
- `analysis/services_breakdown.csv` - 서비스별 분포 (엑셀용)
- `analysis/chat_list_export.csv` - 전체 채팅 목록 테이블 형식 (엑셀용)
- `analysis/missing_chats.csv` - 메시지가 없는 채팅 목록 (있는 경우)
- `analysis/missing_chats.json` - 위와 동일 (JSON 형식)

### 코드 파일
- `models.py` - Pydantic 데이터 모델 (데이터 구조 정의)
- `requirements.txt` - Python 의존성 패키지

## 데이터 구조

### 채팅 목록 (`chat_list_master.jsonl`)
각 줄은 하나의 채팅을 나타내는 JSON 객체이며, 다음 필드를 포함합니다:
- `id` - 채팅 ID
- `service` - 서비스 정보
- `user` - 고객 정보
- `quote` - 견적/가격 정보
- `created_at`, `updated_at` - 타임스탬프
- 그 외... (전체 스키마는 `models.py` 참고)

### 메시지 (`data/messages/chat_<id>.jsonl`)
각 줄은 하나의 메시지를 나타내는 JSON 객체이며, 다음 필드를 포함합니다:
- `id` - 메시지 ID
- `user` - 발신자 정보
- `type` - 메시지 타입 (TEXT, SYSTEM 등)
- `message` - 메시지 내용
- `created_at` - 타임스탬프
- 그 외... (전체 스키마는 `models.py` 참고)

## 빠른 시작

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 데이터 로드 (Python)
```python
import json
from pathlib import Path

# 채팅 목록 로드
chats = []
with open('data/chat_list_master.jsonl', 'r') as f:
    for line in f:
        chats.append(json.loads(line))

# 특정 채팅의 메시지 로드
chat_id = 158837874
messages = []
with open(f'data/messages/chat_{{chat_id}}.jsonl', 'r') as f:
    for line in f:
        messages.append(json.loads(line))
```

### 3. Pydantic 모델 사용 (타입 안전)
```python
from models import ChatItem, MessageItem

# 검증과 함께 파싱
chat = ChatItem(**chats[0])
print(chat.service.title)
print(chat.quote.price)
```

## 분석 파일 활용

CSV 파일을 엑셀/구글 시트에서 열어 쉽게 탐색할 수 있습니다:
- `services_breakdown.csv` - 서비스별 분포 확인
- `chat_list_export.csv` - 전체 데이터를 스프레드시트 형식으로

또는 JSON 파일을 프로그래밍 방식으로 읽을 수 있습니다:
- `data_summary.json` - 빠른 개요
- `data_overview.json` - 상세 통계

## 질문이 있으신가요?

전체 데이터 스키마 정의는 `models.py`를 참고하세요.
"""

    with open(export_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)


def create_requirements_txt(export_dir: Path):
    """Create requirements.txt file."""
    requirements = """# VF-Data Export Dependencies

pydantic>=2.12.3
python-dotenv>=1.2.1
"""

    with open(export_dir / "requirements.txt", 'w', encoding='utf-8') as f:
        f.write(requirements)


def main():
    """Create export package."""
    print("=" * 60)
    print("Creating Export Package")
    print("=" * 60)

    # Create export directory
    print("\n1. Creating export directory...")
    export_dir = create_export_directory()
    print(f"   ✓ Created: {export_dir}")

    # Copy data files
    print("\n2. Copying data files...")
    shutil.copy2(CHAT_LIST_FILE, export_dir / "data" / "chat_list_master.jsonl")
    print(f"   ✓ Copied chat list")

    # Copy message files
    message_files = list(MESSAGES_DIR.glob("chat_*.jsonl"))
    for msg_file in message_files:
        shutil.copy2(msg_file, export_dir / "data" / "messages" / msg_file.name)
    print(f"   ✓ Copied {len(message_files)} message files")

    # Load and analyze data
    print("\n3. Analyzing data...")
    chats = load_chat_list()
    scraped_ids = get_scraped_message_files()
    completeness = analyze_completeness(chats, scraped_ids)
    print(f"   ✓ Analyzed {len(chats)} chats")

    # Analyze messages
    print("\n4. Analyzing messages...")
    message_stats = analyze_message_stats(export_dir / "data" / "messages")
    print(f"   ✓ Analyzed {message_stats['total_messages']} messages")

    # Generate summaries
    print("\n5. Generating summary files...")
    summary = generate_data_summary(chats, completeness, message_stats)
    overview = generate_data_overview(chats, completeness, message_stats)

    with open(export_dir / "analysis" / "data_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open(export_dir / "analysis" / "data_overview.json", 'w', encoding='utf-8') as f:
        json.dump(overview, f, indent=2, ensure_ascii=False)

    if completeness['missing_chats']:
        with open(export_dir / "analysis" / "missing_chats.json", 'w', encoding='utf-8') as f:
            json.dump(completeness['missing_chats'], f, indent=2, ensure_ascii=False)

    print(f"   ✓ Created JSON summaries")

    # Generate CSV exports
    print("\n6. Generating CSV files...")
    save_csv_exports(export_dir, chats, completeness)
    print(f"   ✓ Created CSV exports")

    # Copy models.py
    print("\n7. Copying models.py...")
    shutil.copy2(MODELS_FILE, export_dir / "models.py")
    print(f"   ✓ Copied models.py")

    # Create documentation
    print("\n8. Creating documentation...")
    create_readme(export_dir, summary)
    create_requirements_txt(export_dir)
    print(f"   ✓ Created README.md and requirements.txt")

    # Print summary
    print("\n" + "=" * 60)
    print("Export Package Created!")
    print("=" * 60)
    print(f"\n📦 Location: {export_dir}")
    print(f"\n📊 Summary:")
    print(f"   • Total chats: {completeness['total_chats']}")
    print(f"   • Messages scraped: {completeness['scraped_count']}")
    print(f"   • Completion rate: {completeness['completion_rate']}%")
    print(f"   • Total messages: {message_stats['total_messages']}")
    print(f"   • Avg messages/chat: {message_stats['avg_messages_per_chat']}")

    if completeness['missing_count'] > 0:
        print(f"\n⚠️  Missing {completeness['missing_count']} chat message files")
        print(f"   See: {export_dir / 'analysis' / 'missing_chats.json'}")

    print(f"\n✅ Ready to share with colleagues!")


if __name__ == "__main__":
    main()
