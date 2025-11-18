# AI Personal Assistant

LLM 기반 개인 비서 토이 프로젝트

## 설치 방법

### 1. mac 환경 uv 설치 (Python 패키지 매니저)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 2. 프로젝트 의존성 설치

```bash
cd ai-assistant
uv sync
```

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

# Notion Integration (Optional - for calendar features)
# NOTION_API_KEY=secret_...
# NOTION_DATABASE_ID=...
```

## 실행 방법

### 대화형 모드 (CLI)

```bash
cd ai-assistant
uv run python src/app.py
```

대화형 모드에서 사용 가능한 명령:
- `/help` - 도움말 보기
- `/exit` - 종료

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

- **파일 관리**: 파일 목록 조회, 파일 읽기
- **메모**: 메모 작성, 메모 목록 조회
- **일정**: 일정 조회, 일정 추가 (Notion 또는 mock)
- **웹 검색**: HTTP 요청 및 검색

## Notion 통합 (선택사항)

일정 관리 기능을 Notion과 연동할 수 있습니다:

1. Notion Integration 생성: https://www.notion.so/my-integrations
2. Database 생성 및 Integration 연결
3. `.env` 파일에 설정 추가:
   ```
   NOTION_API_KEY=secret_your_integration_token
   NOTION_DATABASE_ID=your_database_id
   ```

Notion이 설정되지 않은 경우 자동으로 로컬 JSON 파일 기반 mock으로 동작합니다.

## 예시 명령어

- "downloads 폴더 파일 보여줘"
- "오늘 한 일 메모해줘: 프로젝트 설정 완료"
- "오늘 오전 9시에 회의 추가해줘"
- "파이썬 최신 뉴스 검색해줘"

## 프로젝트 구조

```
ai-assistant/
├─ src/
│  ├─ app.py                    # 메인 진입점
│  ├─ config.py                 # 설정
│  ├─ parser/                   # 자연어 파싱
│  │  ├─ request_parser.py      # LLM 기반 파싱
│  │  ├─ schemas.py             # Pydantic 모델
│  │  └─ prompt.txt             # 파싱 프롬프트
│  ├─ router/                   # Agent 라우팅
│  │  └─ agent_router.py        # Intent → Agent 매핑
│  ├─ agents/                   # 각종 Agent 구현
│  │  ├─ base.py                # AgentBase 추상 클래스
│  │  ├─ file_agent.py          # 파일 작업
│  │  ├─ note_agent.py          # 메모 관리
│  │  ├─ calendar_agent.py      # 일정 관리
│  │  ├─ web_agent.py           # 웹 요청
│  │  └─ fallback_agent.py      # 알 수 없는 요청 처리
│  ├─ mcp/                      # MCP 레이어
│  │  ├─ client.py              # MCP 클라이언트
│  │  └─ tools/                 # MCP 툴 구현
│  │     ├─ file_manager.py     # 파일 시스템
│  │     ├─ notes.py            # 메모 저장
│  │     ├─ calendar_mock.py    # Mock 일정
│  │     ├─ notion_calendar.py  # Notion 일정
│  │     └─ http_fetcher.py     # HTTP 요청
│  ├─ data/                     # 데이터 저장소
│  │  ├─ notes.json             # 메모 데이터
│  │  └─ calendar.json          # Mock 일정 데이터
│  └─ utils/                    # 유틸리티
├─ tests/                       # 테스트 코드
├─ logs/                        # 로그 파일
└─ .env                         # 환경 변수
```

## 개발 현황

- ✅ Phase 1: Request Parser (자연어 → 구조화된 요청)
- ✅ Phase 1.5: Agent Router (Intent → Agent 매핑)
- ✅ Phase 2: Agents 구현 (File, Note, Calendar, Web, Fallback)
- ✅ Phase 2.5: MCP Layer (Tools 구현 + Notion 통합)
- ⏳ Phase 3: E2E Integration
- ⏳ Phase 3.5: CLI
- ⏳ Phase 4: Logging & Error Handling
- ⏳ Phase 5: Testing & Validation
- ⏳ Phase 6: Documentation & Deployment
