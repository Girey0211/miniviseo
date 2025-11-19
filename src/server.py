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


class ActionInfo(BaseModel):
    """
    실행된 액션 정보
    
    Attributes:
        intent: 파싱된 의도
        agent: 요청을 처리한 Agent 이름
        status: 처리 상태 (ok 또는 error)
    """
    intent: str
    agent: str
    status: str


class AssistantResponse(BaseModel):
    """
    처리 결과 응답
    
    Attributes:
        response: 자연어로 작성된 응답 메시지
        action_count: 실행된 액션 수
        actions: 실행된 액션들의 정보
        status: 전체 처리 상태 (ok 또는 error)
        session_id: 세션 ID (요청에 포함된 경우)
    """
    response: str
    action_count: int
    actions: list[ActionInfo]
    status: str
    session_id: Optional[str] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "메모를 작성했습니다.",
                    "action_count": 1,
                    "actions": [
                        {"intent": "write_note", "agent": "NoteAgent", "status": "ok"}
                    ],
                    "status": "ok",
                    "session_id": "user-123"
                },
                {
                    "response": "안녕하세요! 부산역 주변 맛집을 찾아서 내일 3시에 일정을 추가했습니다.",
                    "action_count": 3,
                    "actions": [
                        {"intent": "unknown", "agent": "FallbackAgent", "status": "ok"},
                        {"intent": "web_search", "agent": "WebAgent", "status": "ok"},
                        {"intent": "calendar_add", "agent": "CalendarAgent", "status": "ok"}
                    ],
                    "status": "ok",
                    "session_id": "user-123"
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


async def summarize_multi_action_results(
    action_results: list,
    parsed_request,
    conversation_history: list = None
) -> str:
    """
    Generate natural language response from multiple action results using LLM
    
    Args:
        action_results: List of result dictionaries from agents
        parsed_request: Original parsed request with actions
        conversation_history: Previous conversation messages for context
        
    Returns:
        Natural language response string
    """
    # Check if any action failed
    errors = [r for r in action_results if r.get("status") == "error"]
    if errors and len(errors) == len(action_results):
        return f"죄송합니다. 모든 작업이 실패했습니다: {errors[0].get('message', '알 수 없는 오류')}"
    
    # Build detailed results for LLM
    action_details = []
    for idx, (action, result) in enumerate(zip(parsed_request.actions, action_results), 1):
        action_details.append(f"""
작업 {idx}:
- Intent: {action.intent}
- Agent: {action.agent}
- 상태: {result.get('status')}
- 결과: {result.get('result')}
- 메시지: {result.get('message', '')}
""")
    
    # Create prompt for LLM to generate natural response
    prompt = f"""사용자의 요청: "{parsed_request.raw_text}"

실행된 작업들:
{''.join(action_details)}

위 실행 결과들을 바탕으로 사용자에게 자연스러운 한국어로 통합된 응답을 생성해주세요.
- 모든 작업의 결과를 자연스럽게 연결하여 설명
- 간결하고 명확하게 작성
- 결과의 핵심 정보를 포함
- 친근한 톤 사용
- 작업이 여러 개인 경우, 순서대로 설명"""

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
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Fallback to simple response if LLM fails
        logger.error(f"Error in summarize_multi_action_results: {str(e)}")
        success_count = len([r for r in action_results if r.get("status") == "ok"])
        return f"{success_count}개의 작업이 완료되었습니다."


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
    자연어 요청 처리 (다중 액션 지원)
    
    자연어로 작성된 요청을 분석하고 적절한 Agent를 통해 처리합니다.
    한 번의 요청에서 여러 작업을 순차적으로 실행할 수 있습니다.
    
    ## 세션 기반 대화
    
    - **session_id**: 클라이언트에서 제공하는 세션 ID (선택사항)
    - 세션 ID를 제공하면 대화 히스토리가 유지됩니다
    - 세션 ID가 없으면 단일 요청으로 처리됩니다
    - 세션은 7일 동안 유지되며, 사용 시마다 자동 갱신됩니다
    
    ## 지원하는 요청 유형
    
    ### 단일 작업
    - "오늘 한 일 메모해줘: 프로젝트 완료"
    - "내일 오후 3시에 팀 회의 추가해줘"
    - "파이썬 최신 뉴스 검색해줘"
    
    ### 다중 작업 (새로운 기능!)
    - "안녕, 내일 3시에 밥을 먹을거라 부산역 주변 맛집 찾아서 일정 만들어"
      → 1) 인사 응답 2) 웹 검색 3) 일정 추가
    - "파이썬 최신 뉴스 검색하고 메모해줘"
      → 1) 웹 검색 2) 메모 작성
    
    ## 응답 형식
    
    - **response**: 자연어로 작성된 통합 응답 메시지
    - **action_count**: 실행된 액션 수
    - **actions**: 각 액션의 intent, agent, status 정보
    - **status**: 전체 처리 상태 (ok 또는 error)
    - **session_id**: 세션 ID (제공된 경우)
    """
    try:
        logger.info(f"API request received: {request.text}")
        
        # Get or create session if session_id provided
        conversation_history = None
        session = None
        if request.session_id:
            session = await _session_manager.get_or_create_session(request.session_id)
            # Add user message to history
            await session.add_message("user", request.text)
            # Get conversation context for LLM
            conversation_history = await session.get_context_for_llm(limit=10)
            message_count = await session.get_message_count()
            logger.debug(f"Using session: {request.session_id} (history: {message_count} messages)")
        
        # Step 1: Parse request (may contain multiple actions)
        parsed = await parse_request(request.text)
        logger.debug(f"Parsed request with {len(parsed.actions)} action(s)")
        
        # Step 2: Execute each action sequentially
        action_results = []
        previous_results = []  # Store results for context in later actions
        
        for idx, action in enumerate(parsed.actions, 1):
            logger.debug(f"Action {idx}/{len(parsed.actions)} - Intent: {action.intent}, Agent: {action.agent}")
            
            # Route to agent
            agent_class = route_to_agent(action)
            
            if agent_class is None:
                logger.warning(f"No agent found for action {idx}")
                result = {
                    "status": "error",
                    "message": "Agent not found",
                    "result": None
                }
                action_results.append(result)
                continue
            
            # Get agent instance
            agent = _agent_instances.get(action.agent)
            
            if agent is None:
                # Fallback to FallbackAgent
                logger.warning(f"Agent {action.agent} not found, using FallbackAgent")
                agent = _agent_instances.get("FallbackAgent")
                
                if agent is None:
                    logger.error("FallbackAgent not available")
                    result = {
                        "status": "error",
                        "message": "Agent not available",
                        "result": None
                    }
                    action_results.append(result)
                    continue
            
            logger.info(f"Action {idx}: Routing to agent: {agent.get_agent_name()}")
            
            # Execute agent with intent and previous results as context
            params_with_context = {
                **action.params,
                "intent": action.intent,
                "previous_results": previous_results  # Pass previous results for context
            }
            
            result = await agent.handle(params_with_context)
            logger.debug(f"Action {idx} result: {result.get('status')} - {result.get('message', '')}")
            
            # Log error details if action failed
            if result.get("status") == "error":
                logger.error(f"Action {idx} failed: {result.get('message', 'Unknown error')}")
                if "result" in result:
                    logger.error(f"Error details: {result.get('result')}")
            
            action_results.append(result)
            previous_results.append({
                "action": idx,
                "intent": action.intent,
                "agent": action.agent,
                "result": result
            })
        
        # Step 3: Generate natural language response combining all results
        final_response = await summarize_multi_action_results(
            action_results,
            parsed,
            conversation_history
        )
        logger.info(f"Request processed successfully with {len(action_results)} action(s)")
        
        # Determine overall status
        overall_status = "ok"
        if all(r.get("status") == "error" for r in action_results):
            overall_status = "error"
        
        # Add assistant response to session history
        if request.session_id and session:
            await session.add_message(
                "assistant", 
                final_response,
                metadata={
                    "action_count": len(parsed.actions),
                    "actions": [
                        {
                            "intent": action.intent,
                            "agent": action.agent,
                            "status": result.get("status", "ok")
                        }
                        for action, result in zip(parsed.actions, action_results)
                    ]
                }
            )
        
        return AssistantResponse(
            response=final_response,
            action_count=len(parsed.actions),
            actions=[
                ActionInfo(
                    intent=action.intent,
                    agent=action.agent,
                    status=result.get("status", "ok")
                )
                for action, result in zip(parsed.actions, action_results)
            ],
            status=overall_status,
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
