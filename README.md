# AI Personal Assistant

LLM 기반 개인 비서 토이 프로젝트

## 설치 방법

### 1. uv 설치 (Python 패키지 매니저)

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

`.env` 파일을 생성하고 OpenAI API 키를 설정하세요:

```bash
cp .env.example .env
# .env 파일을 열어서 OPENAI_API_KEY를 실제 키로 변경
```

## 실행 방법

```bash
uv run python -m src.app
```

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
