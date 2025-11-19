"""
AI Personal Assistant - HTTP API Server
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI

from parser.request_parser import parse_request
from router.agent_router import route_to_agent, register_agent
from mcp.client import get_mcp_client, register_tool
from config import OPENAI_API_KEY, OPENAI_MODEL
from utils.logger import get_logger

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


def initialize_app():
    """Initialize MCP client, LLM client, and register agents/tools"""
    global _mcp_client, _llm_client, _agent_instances
    
    logger.info("Initializing AI Personal Assistant API Server...")
    
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
    yield
    # Shutdown
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
    
    ### 사용 방법
    1. `/assistant` 엔드포인트에 POST 요청
    2. JSON body에 `text` 필드로 자연어 요청 전달
    3. 응답으로 처리 결과 수신
    
    ### 예시
    ```json
    {
      "text": "오늘 한 일 메모해줘: 프로젝트 완료"
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
    """자연어 요청"""
    text: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "오늘 한 일 메모해줘: 프로젝트 완료"
                },
                {
                    "text": "내일 오후 3시에 팀 회의 추가해줘"
                },
                {
                    "text": "파이썬 최신 뉴스 검색해줘"
                }
            ]
        }
    }


class AssistantResponse(BaseModel):
    """처리 결과 응답"""
    response: str
    intent: str
    agent: str
    status: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "메모를 작성했습니다.",
                    "intent": "write_note",
                    "agent": "NoteAgent",
                    "status": "ok"
                },
                {
                    "response": "일정을 추가했습니다.",
                    "intent": "calendar_add",
                    "agent": "CalendarAgent",
                    "status": "ok"
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    version: str


async def summarize_result(result: dict, parsed_request) -> str:
    """
    Generate natural language response from agent result using LLM
    
    Args:
        result: Result dictionary from agent
        parsed_request: Original parsed request
        
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
        response = await _llm_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "당신은 친절한 AI 개인 비서입니다. 사용자에게 간결하고 명확한 한국어로 응답합니다."},
                {"role": "user", "content": prompt}
            ],
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


@app.post("/assistant", response_model=AssistantResponse, tags=["Assistant"])
async def process_request(request: AssistantRequest):
    """
    자연어 요청 처리
    
    자연어로 작성된 요청을 분석하고 적절한 Agent를 통해 처리합니다.
    
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
    """
    try:
        logger.info(f"API request received: {request.text}")
        
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
        
        # Step 4: Generate natural language response
        final_response = await summarize_result(result, parsed)
        logger.info("Request processed successfully")
        
        return AssistantResponse(
            response=final_response,
            intent=parsed.intent,
            agent=parsed.agent,
            status=result.get("status", "ok")
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
