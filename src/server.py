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
    description="LLM-powered personal assistant with natural language processing",
    version="0.1.0",
    lifespan=lifespan
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
    text: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "text": "오늘 한 일 메모해줘: 프로젝트 완료"
            }]
        }
    }


class AssistantResponse(BaseModel):
    response: str
    intent: str
    agent: str
    status: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "response": "메모를 작성했습니다.",
                "intent": "write_note",
                "agent": "NoteAgent",
                "status": "ok"
            }]
        }
    }


class HealthResponse(BaseModel):
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


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(status="ok", version="0.1.0")


@app.post("/assistant", response_model=AssistantResponse)
async def process_request(request: AssistantRequest):
    """
    Process natural language request and return response
    
    Args:
        request: AssistantRequest with text field
        
    Returns:
        AssistantResponse with response, intent, agent, and status
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
