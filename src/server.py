"""
AI Personal Assistant - HTTP API Server
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI

from parser.request_parser import parse_request
from router.agent_router import route_to_agent, register_agent
from mcp.client import get_mcp_client, register_tool
from config import OPENAI_API_KEY, OPENAI_MODEL
from utils.logger import get_logger
from session import get_session_manager

# Import agents
from agents.note_agent import NoteAgent
from agents.calendar_agent import CalendarAgent
from agents.web_agent import WebAgent
from agents.fallback_agent import FallbackAgent

# Import MCP tools
from mcp.tools import notes, http_fetcher, notion_calendar, notion_notes

logger = get_logger()

# Global instances
_mcp_client = None
_llm_client = None
_agent_instances = {}
_session_manager = None


def initialize_app():
    """Initialize MCP client, LLM client, and register agents/tools"""
    global _mcp_client, _llm_client, _agent_instances, _session_manager
    
    logger.info("Initializing AI Personal Assistant API Server...")
    
    # Initialize session manager
    _session_manager = get_session_manager()
    logger.debug("Session manager initialized")
    
    # Initialize MCP client
    _mcp_client = get_mcp_client()
    logger.debug("MCP client initialized")
    
    # Register MCP tools
    register_tool("notes", notes)
    register_tool("http_fetcher", http_fetcher)
    register_tool("notion_calendar", notion_calendar)
    register_tool("notion_notes", notion_notes)
    logger.info("MCP tools registered")
    
    # Initialize LLM client
    _llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.debug(f"LLM client initialized with model: {OPENAI_MODEL}")
    
    # Create agent instances
    _agent_instances = {
        "NoteAgent": NoteAgent(mcp_client=_mcp_client, llm_client=_llm_client),
        "CalendarAgent": CalendarAgent(mcp_client=_mcp_client, llm_client=_llm_client),
        "WebAgent": WebAgent(mcp_client=_mcp_client),
        "FallbackAgent": FallbackAgent(mcp_client=_mcp_client, llm_client=_llm_client),
    }
    
    # Register agents with router
    for agent_name, agent_instance in _agent_instances.items():
        register_agent(agent_name, agent_instance)
    
    logger.info(f"Agents registered: {', '.join(_agent_instances.keys())}")
    logger.info("API Server initialization complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    initialize_app()
    # Start session cleanup task
    await _session_manager.start_cleanup_task(interval_minutes=10)
    yield
    # Shutdown
    _session_manager.stop_cleanup_task()
    logger.info("Shutting down API Server...")


# Create FastAPI app
app = FastAPI(
    title="AI Personal Assistant API",
    description="""
    ## LLM 기반 개인 비서 API
    
    자연어 요청을 처리하여 다양한 작업을 수행합니다.
    
    ### 지원 기능
    - 📝 메모 작성 및 조회 (Notion 통합)
    - 📅 일정 관리 (Notion 통합)
    - 🔍 웹 검색 및 요약
    - 💬 세션 기반 대화 히스토리 관리
    
    ### 기본 사용 방법 (세션 없이)
    1. `/assistant` 엔드포인트에 POST 요청
    2. JSON body에 `text` 필드로 자연어 요청 전달
    3. 응답으로 처리 결과 수신
    
    ```json
    {
      "text": "오늘 한 일 메모해줘: 프로젝트 완료"
    }
    ```
    
    ### 세션 기반 대화 (권장)
    `session_id`를 포함하면 대화 히스토리가 유지됩니다.
    
    **첫 번째 요청:**
    ```json
    {
      "text": "안녕하세요",
      "session_id": "user-123"
    }
    ```
    
    **두 번째 요청 (같은 세션):**
    ```json
    {
      "text": "아까 말한 내용 기억해?",
      "session_id": "user-123"
    }
    ```
    
    ### 세션 관리
    - **자동 생성**: `session_id`를 처음 사용하면 자동으로 세션 생성
    - **만료 기한**: 세션 생성 시 7일 후 만료
    - **자동 갱신**: 세션 사용 시마다 만료 기한 7일 연장
    - **자동 정리**: 만료된 세션은 자동으로 삭제
    - **세션 ID 형식**: 자유롭게 지정 가능 (예: "user-123", "session-abc-def")
    
    ### 세션 관리 API
    - `GET /sessions/{session_id}` - 세션 정보 및 대화 히스토리 조회
      - `?page=N` 파라미터로 페이지 지정 (0부터 시작, 0 = 최신)
      - `?page_size=N` 파라미터로 페이지당 메시지 수 (기본 10, 최대 50)
    - `DELETE /sessions/{session_id}` - 세션 삭제
    - `GET /sessions-stats` - 전체 세션 통계
    
    ### 대화 히스토리 조회 예시
    ```
    GET /sessions/user-123                    # 최신 10개
    GET /sessions/user-123?page=1             # 그 다음 10개
    GET /sessions/user-123?page=0&page_size=20  # 최신 20개
    ```
    
    **응답 예시:**
    ```json
    {
      "session_id": "user-123",
      "message_count": 10,
      "messages": [
        {"role": "user", "content": "안녕하세요", "timestamp": "..."},
        {"role": "assistant", "content": "안녕하세요!", "timestamp": "..."}
      ]
    }
    ```
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class AssistantRequest(BaseModel):
    """
    자연어 요청
    
    Attributes:
        text: 자연어로 작성된 요청 내용
        session_id: 세션 ID (선택사항). 제공하면 대화 히스토리가 유지됩니다.
    """
    text: str
    session_id: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "오늘 한 일 메모해줘: 프로젝트 완료",
                    "session_id": "user-123"
                },
                {
                    "text": "내일 오후 3시에 팀 회의 추가해줘",
                    "session_id": "user-123"
                },
                {
                    "text": "파이썬 최신 뉴스 검색해줘"
                },
                {
                    "text": "안녕하세요, 메모 작성 도와주세요",
                    "session_id": "session-abc-def-123"
                }
            ]
        }
    }


class AssistantResponse(BaseModel):
    """
    처리 결과 응답
    
    Attributes:
        response: 자연어로 작성된 응답 메시지
        intent: 파싱된 의도 (write_note, list_notes, calendar_add, etc.)
        agent: 요청을 처리한 Agent 이름
        status: 처리 상태 (ok 또는 error)
        session_id: 세션 ID (요청에 포함된 경우)
    """
    response: str
    intent: str
    agent: str
    status: str
    session_id: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "메모를 작성했습니다.",
                    "intent": "write_note",
                    "agent": "NoteAgent",
                    "status": "ok",
                    "session_id": "user-123"
                },
                {
                    "response": "일정을 추가했습니다.",
                    "intent": "calendar_add",
                    "agent": "CalendarAgent",
                    "status": "ok",
                    "session_id": "user-123"
                },
                {
                    "response": "검색 결과를 요약했습니다: ...",
                    "intent": "web_search",
                    "agent": "WebAgent",
                    "status": "ok",
                    "session_id": None
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    version: str


class MessageInfo(BaseModel):
    """
    메시지 정보
    
    Attributes:
        role: 메시지 역할 (user 또는 assistant)
        content: 메시지 내용
        timestamp: 메시지 생성 시각 (ISO 8601 형식)
        metadata: 추가 메타데이터 (intent, agent 등)
    """
    role: str
    content: str
    timestamp: str
    metadata: dict = {}


class SessionInfoResponse(BaseModel):
    """
    세션 정보 응답
    
    Attributes:
        session_id: 세션 ID
        message_count: 세션에 저장된 총 메시지 수
        created_at: 세션 생성 시각 (ISO 8601 형식)
        last_accessed: 마지막 접근 시각 (ISO 8601 형식)
        messages: 대화 히스토리 (페이지 단위)
    """
    session_id: str
    message_count: int
    created_at: str
    last_accessed: str
    messages: list[MessageInfo] = []
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "user-123",
                    "message_count": 10,
                    "created_at": "2025-01-01T10:00:00",
                    "last_accessed": "2025-01-05T15:30:00",
                    "messages": [
                        {
                            "role": "user",
                            "content": "안녕하세요",
                            "timestamp": "2025-01-01T10:00:00",
                            "metadata": {}
                        },
                        {
                            "role": "assistant",
                            "content": "안녕하세요! 무엇을 도와드릴까요?",
                            "timestamp": "2025-01-01T10:00:05",
                            "metadata": {"intent": "greeting", "agent": "FallbackAgent"}
                        }
                    ]
                }
            ]
        }
    }


class SessionStatsResponse(BaseModel):
    """
    세션 통계 응답
    
    Attributes:
        active_sessions: 현재 활성 세션 수
        total_messages: 전체 메시지 수
    """
    active_sessions: int
    total_messages: int
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "active_sessions": 42,
                    "total_messages": 1337
                }
            ]
        }
    }


async def summarize_result(result: dict, parsed_request, conversation_history: list = None) -> str:
    """
    Generate natural language response from agent result using LLM
    
    Args:
        result: Result dictionary from agent
        parsed_request: Original parsed request
        conversation_history: Previous conversation messages for context
        
    Returns:
        Natural language response string
    """
    if result.get("status") == "error":
        return f"죄송합니다. 오류가 발생했습니다: {result.get('message', '알 수 없는 오류')}"
    
    # Create prompt for LLM to generate natural response
    prompt = f"""사용자의 요청: "{parsed_request.raw_text}"
Intent: {parsed_request.intent}
실행 결과: {result.get('result')}

위 실행 결과를 바탕으로 사용자에게 자연스러운 한국어로 응답을 생성해주세요.
- 간결하고 명확하게 작성
- 결과의 핵심 정보를 포함
- 친근한 톤 사용"""

    try:
        # Build messages with conversation history
        messages = [
            {"role": "system", "content": "당신은 친절한 AI 개인 비서입니다. 사용자에게 간결하고 명확한 한국어로 응답합니다."}
        ]
        
        # Add conversation history if available
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        response = await _llm_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error in summarize_result: {str(e)}")
        return f"작업이 완료되었습니다. 결과: {result.get('result')}"


@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root():
    """
    루트 엔드포인트
    
    서버 상태를 확인합니다.
    """
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """
    헬스체크 엔드포인트
    
    서버가 정상적으로 동작하는지 확인합니다.
    """
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/sessions/{session_id}", response_model=SessionInfoResponse, tags=["Session"])
async def get_session_info(session_id: str, page: int = 0, page_size: int = 10):
    """
    세션 정보 및 대화 히스토리 조회
    
    특정 세션의 정보와 대화 히스토리를 페이지 단위로 조회합니다.
    
    **Parameters:**
    - **session_id**: 조회할 세션 ID
    - **page**: 페이지 번호 (0부터 시작, 0 = 최신 메시지)
    - **page_size**: 페이지당 메시지 수 (기본값: 10, 최대: 50)
    
    **Returns:**
    - 세션 ID, 메시지 수, 생성 시각, 마지막 접근 시각, 대화 히스토리
    
    **Example:**
    ```
    GET /sessions/user-123              # 최신 10개
    GET /sessions/user-123?page=1       # 그 다음 10개
    GET /sessions/user-123?page=0&page_size=20  # 최신 20개
    ```
    """
    session = await _session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    # Validation
    if page < 0:
        page = 0
    if page_size > 50:
        page_size = 50
    elif page_size < 1:
        page_size = 1
    
    message_count = await session.get_message_count()
    messages = await session.get_messages(page=page, page_size=page_size)
    
    # Convert messages to MessageInfo format
    message_infos = [
        MessageInfo(
            role=msg["role"],
            content=msg["content"],
            timestamp=msg["timestamp"],
            metadata=msg.get("metadata", {})
        )
        for msg in messages
    ]
    
    return SessionInfoResponse(
        session_id=session.session_id,
        message_count=message_count,
        created_at=session.created_at.isoformat(),
        last_accessed=session.last_accessed.isoformat(),
        messages=message_infos
    )


@app.delete("/sessions/{session_id}", tags=["Session"])
async def delete_session(session_id: str):
    """
    세션 삭제
    
    특정 세션과 대화 히스토리를 완전히 삭제합니다.
    
    **Parameters:**
    - **session_id**: 삭제할 세션 ID
    
    **Returns:**
    - 삭제 성공 메시지
    
    **Example:**
    ```
    DELETE /sessions/user-123
    ```
    
    **Note:** 삭제된 세션은 복구할 수 없습니다.
    """
    deleted = await _session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    return {"status": "ok", "message": "세션이 삭제되었습니다"}


@app.get("/sessions-stats", response_model=SessionStatsResponse, tags=["Session"])
async def get_session_stats():
    """
    세션 통계 조회
    
    현재 활성화된 세션 통계를 조회합니다.
    
    **Returns:**
    - **active_sessions**: 현재 활성 세션 수
    - **total_messages**: 전체 메시지 수
    
    **Example:**
    ```
    GET /sessions-stats
    ```
    """
    active_count = await _session_manager.get_active_session_count()
    total_messages = await _session_manager.get_total_message_count()
    
    return SessionStatsResponse(
        active_sessions=active_count,
        total_messages=total_messages
    )


@app.post("/assistant", response_model=AssistantResponse, tags=["Assistant"])
async def process_request(request: AssistantRequest):
    """
    자연어 요청 처리
    
    자연어로 작성된 요청을 분석하고 적절한 Agent를 통해 처리합니다.
    
    ## 세션 기반 대화
    
    - **session_id**: 클라이언트에서 제공하는 세션 ID (선택사항)
    - 세션 ID를 제공하면 대화 히스토리가 유지됩니다
    - 세션 ID가 없으면 단일 요청으로 처리됩니다
    - 세션은 60분 동안 유지되며, 이후 자동으로 삭제됩니다
    
    ## 지원하는 요청 유형
    
    ### 메모 작성
    - "오늘 한 일 메모해줘: 프로젝트 완료"
    - "회의록 작성해줘: 팀 미팅 내용"
    
    ### 메모 조회
    - "내 메모 목록 보여줘"
    - "메모 리스트 알려줘"
    
    ### 일정 추가
    - "내일 오후 3시에 팀 회의 추가해줘"
    - "다음주 월요일 오전 10시에 발표 일정 잡아줘"
    
    ### 일정 조회
    - "이번 주 일정 보여줘"
    - "오늘 일정 알려줘"
    
    ### 웹 검색
    - "파이썬 최신 뉴스 검색해줘"
    - "OpenAI API 문서 찾아줘"
    
    ## 응답 형식
    
    - **response**: 자연어로 작성된 응답 메시지
    - **intent**: 파싱된 의도 (write_note, list_notes, calendar_add, calendar_list, web_search 등)
    - **agent**: 요청을 처리한 Agent 이름
    - **status**: 처리 상태 (ok 또는 error)
    - **session_id**: 세션 ID (제공된 경우)
    """
    try:
        logger.info(f"API request received: {request.text}")
        
        # Get or create session if session_id provided
        conversation_history = None
        if request.session_id:
            session = await _session_manager.get_or_create_session(request.session_id)
            # Add user message to history
            await session.add_message("user", request.text)
            # Get conversation context for LLM
            conversation_history = await session.get_context_for_llm(limit=10)
            message_count = await session.get_message_count()
            logger.debug(f"Using session: {request.session_id} (history: {message_count} messages)")
        
        # Step 1: Parse request
        parsed = await parse_request(request.text)
        logger.debug(f"Parsed - Intent: {parsed.intent}, Agent: {parsed.agent}")
        
        # Step 2: Route to agent
        agent_class = route_to_agent(parsed)
        
        if agent_class is None:
            logger.warning("No agent found for request")
            raise HTTPException(status_code=400, detail="요청을 처리할 수 없습니다")
        
        # Get agent instance
        agent = _agent_instances.get(parsed.agent)
        
        if agent is None:
            logger.warning(f"Agent {parsed.agent} not found, using FallbackAgent")
            agent = _agent_instances.get("FallbackAgent")
            
            if agent is None:
                logger.error("FallbackAgent not available")
                raise HTTPException(status_code=500, detail="Agent not available")
        
        logger.info(f"Routing to agent: {agent.get_agent_name()}")
        
        # Step 3: Execute agent
        params_with_intent = {**parsed.params, "intent": parsed.intent}
        result = await agent.handle(params_with_intent)
        logger.debug(f"Agent result: {result.get('status')}")
        
        # Step 4: Generate natural language response with conversation history
        final_response = await summarize_result(result, parsed, conversation_history)
        logger.info("Request processed successfully")
        
        # Add assistant response to session history
        if request.session_id:
            await session.add_message(
                "assistant", 
                final_response,
                metadata={
                    "intent": parsed.intent,
                    "agent": parsed.agent,
                    "status": result.get("status", "ok")
                }
            )
        
        return AssistantResponse(
            response=final_response,
            intent=parsed.intent,
            agent=parsed.agent,
            status=result.get("status", "ok"),
            session_id=request.session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


def main():
    """Entry point for server"""
    import uvicorn
    import signal
    
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal, stopping server...")
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting AI Personal Assistant API Server...")
    logger.info("Swagger UI: http://0.0.0.0:8000/docs")
    logger.info("ReDoc: http://0.0.0.0:8000/redoc")
    logger.info("Press Ctrl+C to stop")
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
