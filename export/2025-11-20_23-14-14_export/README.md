# VF-Data 데이터 패키지

**생성 일시:** 2025-11-20T23:14:22.783499

## 데이터셋 개요

- **전체 채팅 수:** 16102
- **메시지 수집 완료:** 16102
- **수집 완료율:** 100.0%
- **가장 많은 서비스:** 이력서/자소서 컨설팅
- **계약 성사율:** 6.14%
- **전체 메시지 수:** 285864

## 날짜 범위

**중요:** 이 데이터셋은 최근 활동 날짜를 기준으로 필터링되었습니다.

- **생성 날짜 범위:** 2020-08-19T09:12:21 to 2025-11-03T14:52:29.859000
  - 채팅이 처음 생성된 기간
- **업데이트 날짜 범위 (필터 기준):** 2020-08-21T07:30:43.219000 to 2025-11-03T15:01:16.317000 (1900일)
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
with open(f'data/messages/chat_{chat_id}.jsonl', 'r') as f:
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
