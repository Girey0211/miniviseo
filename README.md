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
uv sync
```

### 3. 환경 변수 설정

`.env` 파일에 유효한 OpenAI API 키를 설정:

`.env` 파일 예시:
```
OPENAI_API_KEY=sk-proj-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini
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
- **일정**: 일정 조회, 일정 추가 (mock)
- **웹 검색**: HTTP 요청 및 검색

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
│  ├─ router/                   # Agent 라우팅
│  ├─ agents/                   # 각종 Agent 구현
│  ├─ mcp/                      # MCP 레이어
│  ├─ data/                     # 데이터 저장소
│  └─ utils/                    # 유틸리티
├─ logs/                        # 로그 파일
└─ .env                         # 환경 변수
```
