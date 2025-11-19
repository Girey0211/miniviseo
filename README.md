# AI Personal Assistant

LLM 기반 개인 비서 토이 프로젝트 - **다중 액션 지원**

## 빠른 시작

```bash
# 1. 프로젝트 클론 및 이동
cd ai-assistant

# 2. 의존성 설치
uv sync

# 3. .env 파일에 OpenAI API 키 설정
# OPENAI_API_KEY=sk-proj-your-key-here

# 4. 실행
uv run cli
```

## 설치 방법

### 1. mac 환경 uv 설치 (Python 패키지 매니저)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 2. 프로젝트 의존성 설치 및 명령어 등록

```bash
cd ai-assistant
uv sync
```

이 명령어는 의존성을 설치하고 `aia`, `assistant`, `ai-assistant` 명령어를 등록합니다.

### 3. 환경 변수 설정

`.env` 파일에 유효한 OpenAI API 키를 설정하세요:

```bash
# .env 파일을 열어서 OPENAI_API_KEY를 실제 키로 변경
# OpenAI API 키는 https://platform.openai.com/api-keys 에서 발급받을 수 있습니다
# 주의: API 키에 충분한 크레딧이 있어야 합니다
```

`.env` 파일 예시:
```
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Notion Integration (Required for notes and calendar features)
NOTION_API_KEY=your_integration_token
NOTION_CALENDAR_DATABASE_ID=your_calendar_database_id
NOTION_NOTES_DATABASE_ID=your_notes_database_id
```

## 실행 방법

### 대화형 모드 (CLI)

실행 방법들:

```bash
# 전체 명령어
uv run cli

# Python 모듈로 실행
uv run python src/app.py

# 또는
python -m src.app
```

**시작 화면:**
```
┌─────────────────────────────────────────┐
│ AI Personal Assistant                   │
│ 자연어로 명령을 입력하세요. 도움말: /help │
└─────────────────────────────────────────┘
```

**특수 명령:**

세션 관리:
- `/session` - 세션 목록 보기
- `/session-select <번호|ID>` - 세션 전환 (예: `/session-select 2` 또는 `/session-select cli-abc123`)
- `/session-delete <번호|ID>` - 세션 삭제 (예: `/session-delete 3` 또는 `/session-delete cli-abc123`)

기타:
- `/help` - 도움말 및 세션 정보 보기
- `/history` - 현재 세션의 대화 히스토리 보기 (최근 10개)
- `/clear` - 현재 세션의 대화 히스토리 초기화
- `/debug` - 디버그 모드 토글 (로그 파일 경로 표시)
- `/exit` - 종료

**세션 관리:**
- CLI 실행 시 항상 새로운 세션이 생성됩니다
- `/session` 명령으로 이전 세션 목록을 볼 수 있습니다
- `/session-select` 명령으로 다른 세션으로 전환할 수 있습니다 (번호 또는 세션 ID 사용)
- 세션 전환 시 메시지가 없는 빈 세션은 자동으로 삭제됩니다
- `/session-delete` 명령으로 세션을 삭제할 수 있습니다 (번호 또는 세션 ID 사용)
- 현재 세션 삭제 시 자동으로 새 세션이 생성됩니다
- 각 세션은 독립적인 대화 히스토리를 유지합니다
- 이전 대화 내용을 기억하여 문맥을 이해합니다

**세션 명령 사용 예시:**
```bash
# 세션 목록 보기
/session

# 출력:
# 1. cli-abc123 - 5개 메시지 - 2025-01-01 10:00 ← 현재
# 2. cli-def456 - 10개 메시지 - 2025-01-01 09:00
# 3. cli-ghi789 - 0개 메시지 - 2025-01-01 08:00

# 세션 2로 전환 (번호 사용)
/session-select 2

# 또는 세션 ID로 전환
/session-select cli-def456

# 세션 3 삭제 (번호 사용)
/session-delete 3

# 또는 세션 ID로 삭제
/session-delete cli-ghi789
```

### HTTP API 서버 모드

백엔드 서버로 실행하여 HTTP API를 통해 요청을 처리할 수 있습니다:

```bash
# 서버 실행 (기본 포트: 8000)
uv run server

# 또는 Python으로 직접 실행
uv run python src/server.py

# 또는 uvicorn으로 직접 실행
uv run uvicorn src.server:app --host 0.0.0.0 --port 8000

# 개발 모드 (자동 리로드)
uv run uvicorn src.server:app --reload
```

서버 실행 후:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **종료**: Ctrl+C

#### API 엔드포인트

**Health Check**
```bash
GET /health
```

**요청 처리 (세션 없이)**
```bash
POST /assistant
Content-Type: application/json

{
  "text": "오늘 한 일 메모해줘: 프로젝트 완료"
}
```

**요청 처리 (세션 기반 대화)**
```bash
POST /assistant
Content-Type: application/json

{
  "text": "오늘 한 일 메모해줘: 프로젝트 완료",
  "session_id": "user-123-session"
}
```

**응답 예시 (단일 액션)**
```json
{
  "response": "메모를 작성했습니다.",
  "action_count": 1,
  "actions": [
    {
      "intent": "write_note",
      "agent": "NoteAgent",
      "status": "ok"
    }
  ],
  "status": "ok",
  "session_id": "user-123-session"
}
```

**다중 액션 요청 예시**
```bash
POST /assistant
Content-Type: application/json

{
  "text": "안녕, 내일 3시에 밥을 먹을거라 부산역 주변 맛집 찾아서 일정 만들어",
  "session_id": "user-123"
}
```

**다중 액션 응답 예시**
```json
{
  "response": "안녕하세요! 부산역 주변 맛집을 검색했습니다. 1) 부산집 - 돼지국밥 전문점, 2) 해운대식당 - 회 전문점, 3) 밀면골목 - 밀면 전문점. 내일 오후 3시에 '밥약속' 일정을 추가했습니다.",
  "action_count": 3,
  "actions": [
    {
      "intent": "unknown",
      "agent": "FallbackAgent",
      "status": "ok"
    },
    {
      "intent": "web_search",
      "agent": "WebAgent",
      "status": "ok"
    },
    {
      "intent": "calendar_add",
      "agent": "CalendarAgent",
      "status": "ok"
    }
  ],
  "status": "ok",
  "session_id": "user-123"
}
```

**세션 관리**
```bash
# 세션 정보 조회 (페이지네이션)
GET /sessions/{session_id}?page=0&page_size=10

# 세션 삭제
DELETE /sessions/{session_id}

# 세션 통계
GET /sessions-stats
```

**페이지네이션 파라미터**
- `page`: 페이지 번호 (0부터 시작, 0 = 최신 메시지)
- `page_size`: 페이지당 메시지 수 (기본값: 10, 최대: 50)

#### cURL 예시

```bash
# Health check
curl http://localhost:8000/health

# 메모 작성 (세션 없이)
curl -X POST http://localhost:8000/assistant \
  -H "Content-Type: application/json" \
  -d '{"text": "메모 작성해줘: 테스트 메모"}'

# 세션 기반 대화
curl -X POST http://localhost:8000/assistant \
  -H "Content-Type: application/json" \
  -d '{"text": "안녕하세요", "session_id": "user-123"}'

curl -X POST http://localhost:8000/assistant \
  -H "Content-Type: application/json" \
  -d '{"text": "메모 작성해줘: 프로젝트 완료", "session_id": "user-123"}'

# 세션 정보 조회 (최신 10개)
curl http://localhost:8000/sessions/user-123

# 세션 정보 조회 (page 1, 그 다음 10개)
curl http://localhost:8000/sessions/user-123?page=1

# 세션 정보 조회 (page 0, 최신 20개)
curl "http://localhost:8000/sessions/user-123?page=0&page_size=20"

# 세션 삭제
curl -X DELETE http://localhost:8000/sessions/user-123

# 세션 통계
curl http://localhost:8000/sessions-stats

# 웹 검색
curl -X POST http://localhost:8000/assistant \
  -H "Content-Type: application/json" \
  -d '{"text": "파이썬 최신 뉴스 검색해줘"}'
```

### 단위 테스트 실행

```bash
cd ai-assistant
uv run pytest tests/ -v
```

### 가상환경 활성화 후 실행

```bash
cd ai-assistant
source .venv/bin/activate
python src/app.py
```

## 주의사항

- **OpenAI API 키 필수**: 유효한 API 키와 충분한 크레딧이 필요합니다
- API 키가 없거나 quota가 초과된 경우 모든 요청이 `unknown` intent로 fallback됩니다
- 테스트 실행 시 mock을 사용하므로 API 키 없이도 테스트 가능합니다

## 지원하는 기능

- **다중 액션 지원** ⭐ NEW: 한 번의 요청에서 여러 작업을 순차적으로 실행
- **메모**: 메모 작성, 메모 목록 조회 (Notion 통합)
- **일정**: 일정 조회, 일정 추가 (Notion 통합)
- **웹 검색**: 검색 결과 자동 수집 및 LLM 요약
- **CLI 모드**: 대화형 인터페이스
- **API 서버 모드**: HTTP REST API 제공
- **세션 기반 대화**: 클라이언트별 대화 히스토리 관리
- **영구 저장소**: SQLite 기반 세션 및 메시지 저장 (Repository 패턴)
- **자동 만료**: 세션 사용 시마다 7일 연장, 미사용 시 자동 삭제

## Notion 통합 (필수)

메모 및 일정 관리 기능은 Notion API를 사용합니다.

### 1. Notion Integration 생성

1. https://www.notion.so/my-integrations 에서 새 Integration 생성
2. Integration 이름 설정 (예: "AI Assistant")
3. Integration Token 복사

### 2. Notion 데이터베이스 생성

#### 일정 데이터베이스

1. Notion에서 새 Database 생성
2. **정확히** 다음 속성 추가 (이름과 타입이 정확해야 함):
   - **이름** 또는 **제목** (Title 타입) - 데이터베이스의 기본 제목 속성
   - **날짜** (Date 타입) - 일정 날짜 및 시간
   - **설명** (Rich Text 타입) - 일정 설명 ⭐ **강력 권장**
3. Database를 Integration과 연결 (Share → Integration 선택)
4. Database ID 복사 (URL에서 확인 가능)

**중요**: 
- Title 속성은 `이름` 또는 `제목` 모두 가능 (자동 감지)
- `설명` 속성이 없으면 웹 검색 결과 등 상세 정보를 저장할 수 없습니다
- 다중 액션 기능을 사용하려면 `설명` 속성 추가를 강력히 권장합니다

#### 메모 데이터베이스

1. Notion에서 새 Database 생성
2. **정확히** 다음 속성 추가 (이름과 타입이 정확해야 함):
   - **제목** (Title 타입) - 데이터베이스의 기본 제목 속성
   - **내용** (Rich Text 타입) - 메모 내용
   - **생성일** (Created time 타입) - 자동 생성 시간 (선택사항)
3. Database를 Integration과 연결 (Share → Integration 선택)
4. Database ID 복사 (URL에서 확인 가능)

**중요**: 속성 이름은 정확히 한글로 `제목`, `내용`이어야 합니다.

### 3. 환경 변수 설정

`.env` 파일에 Notion 설정 추가:

```
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Notion Integration
NOTION_API_KEY=your_integration_token
NOTION_CALENDAR_DATABASE_ID=your_calendar_database_id
NOTION_NOTES_DATABASE_ID=your_notes_database_id
```

**주의**: Notion이 설정되지 않은 경우 메모 및 일정 기능 사용 시 에러 메시지가 표시됩니다.

## 예시 명령어

### 단일 작업

#### 메모 관리
- "오늘 한 일 메모해줘: 프로젝트 설정 완료"
- "회의록 작성해줘: 제목은 팀 미팅, 내용은 Q1 목표 논의"
- "내 메모 목록 보여줘"

#### 일정 관리
- "오늘 오전 9시에 회의 추가해줘"
- "내일 오후 2시에 치과 예약 추가"
- "이번 주 일정 보여줘"

#### 웹 검색
- "파이썬 최신 뉴스 검색해줘"
- "OpenAI API 문서 찾아줘"

### 다중 작업 ⭐ NEW

한 번의 요청으로 여러 작업을 순차적으로 실행할 수 있습니다:

- **"안녕, 내일 3시에 밥을 먹을거라 부산역 주변 맛집 찾아서 일정 만들어"**
  1. 인사 응답 (FallbackAgent)
  2. 부산역 주변 맛집 검색 (WebAgent)
  3. 내일 3시 일정 추가 - 검색 결과가 일정 설명에 자동 포함 (CalendarAgent)

- **"부산 맛집 찾아서 메모 남겨"**
  1. 부산 맛집 검색 (WebAgent)
  2. 검색 결과를 메모로 저장 - 참고 링크 포함 (NoteAgent)

- **"파이썬 최신 뉴스 검색하고 메모해줘"**
  1. 파이썬 뉴스 검색 (WebAgent)
  2. 검색 결과를 메모로 저장 (NoteAgent)

- **"이번주 일정 보여주고, 내일 오전 10시에 회의 추가해줘"**
  1. 이번주 일정 조회 (CalendarAgent)
  2. 내일 오전 10시 회의 추가 (CalendarAgent)

**컨텍스트 전달**: 이전 액션의 결과가 다음 액션에 자동으로 전달됩니다. 예를 들어 웹 검색 결과가 메모나 일정의 내용으로 사용됩니다.

## 프로젝트 구조

```
ai-assistant/
├─ src/
│  ├─ app.py                    # CLI 메인 진입점
│  ├─ server.py                 # HTTP API 서버
│  ├─ config.py                 # 설정
│  ├─ parser/                   # 자연어 파싱
│  │  ├─ request_parser.py      # LLM 기반 파싱
│  │  ├─ schemas.py             # Pydantic 모델
│  │  └─ prompt.txt             # 파싱 프롬프트
│  ├─ router/                   # Agent 라우팅
│  │  └─ agent_router.py        # Intent → Agent 매핑
│  ├─ agents/                   # 각종 Agent 구현
│  │  ├─ base.py                # AgentBase 추상 클래스
│  │  ├─ note_agent.py          # 메모 관리 (Notion 통합)
│  │  ├─ calendar_agent.py      # 일정 관리 (Notion 통합)
│  │  ├─ web_agent.py           # 웹 검색 및 요약
│  │  └─ fallback_agent.py      # 알 수 없는 요청 처리
│  ├─ mcp/                      # MCP 레이어
│  │  ├─ client.py              # MCP 클라이언트
│  │  └─ tools/                 # MCP 툴 구현
│  │     ├─ notion_notes.py     # Notion 메모 관리
│  │     ├─ notion_calendar.py  # Notion 일정 관리
│  │     └─ http_fetcher.py     # HTTP 요청 및 검색
│  ├─ session/                  # 세션 관리
│  │  ├─ session_manager.py     # 대화 히스토리 관리
│  │  ├─ repository.py          # Repository 추상 인터페이스
│  │  └─ sqlite_repository.py   # SQLite 구현체
│  └─ utils/                    # 유틸리티
│     └─ logger.py              # 로깅 설정
├─ tests/                       # 테스트 코드
├─ logs/                        # 로그 파일
└─ .env                         # 환경 변수
```

## 세션 관리

### CLI 모드
- **자동 세션 생성**: 첫 실행 시 자동으로 세션 생성
- **세션 ID 저장**: `~/.ai-assistant-session` 파일에 저장
- **대화 히스토리**: 이전 대화 내용을 기억하여 문맥 이해
- **명령어**: `/clear`로 히스토리 초기화, `/history`로 히스토리 보기

### API 서버 모드
- **만료 기한**: 세션 생성 시 7일 후 만료
- **자동 갱신**: 세션 사용 시마다 만료 기한이 7일 연장
- **자동 정리**: 만료된 세션은 백그라운드 작업으로 자동 삭제 (10분마다)
- **영구 저장**: SQLite에 저장되어 서버 재시작 후에도 유지

예시:
- 세션 생성: 2025-01-01 → 만료: 2025-01-08
- 2025-01-05에 사용 → 만료: 2025-01-12 (7일 연장)
- 2025-01-12까지 미사용 → 자동 삭제

## 개발 현황

- ✅ Phase 1: Request Parser (자연어 → 구조화된 요청)
- ✅ Phase 1.5: Agent Router (Intent → Agent 매핑)
- ✅ Phase 2: Agents 구현 (Note, Calendar, Web, Fallback)
- ✅ Phase 2.5: MCP Layer (Tools 구현 + Notion 통합)
- ✅ Phase 3: E2E Integration (완전한 파이프라인)
- ✅ Phase 3.5: CLI (대화형 인터페이스)
- ✅ Phase 4: Logging & Error Handling (loguru 기반)
- ✅ Phase 5: Testing & Validation (178개 테스트 통과)
- ✅ Phase 6: Documentation & Deployment
- ✅ Phase 7: Session Management (SQLite 영구 저장소 + 자동 만료)

## 테스트 현황

- **총 178개 테스트 모두 통과** ✅
- Parser 테스트: 13개
- Agent 테스트: 33개
- MCP Tools 테스트: 25개
- Router 테스트: 23개
- Notion 통합 테스트: 13개
- E2E 통합 테스트: 18개
- API 서버 테스트: 17개
- 세션 관리 테스트: 20개
- SQLite Repository 테스트: 12개
- 워닝: 0개
- 스킵: 0개

**참고**: 
- 모든 테스트는 OpenAI API 키 없이도 실행 가능 (mock 사용)
- Notion API 키가 설정된 경우 실제 API 테스트 실행
- Notion API 키가 없는 경우 에러 처리 테스트만 실행

## 로깅

애플리케이션 로그는 `logs/assistant.log`에 저장됩니다:
- 자동 rotation (10MB)
- 7일간 보관
- 압축 저장 (zip)

디버그 모드(`/debug`)를 활성화하면 로그 파일 경로가 표시됩니다.
