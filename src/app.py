"""
AI Personal Assistant - Main Application
"""
import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from openai import AsyncOpenAI

from parser.request_parser import parse_request
from router.agent_router import route_to_agent, register_agent
from mcp.client import get_mcp_client, register_tool
from config import OPENAI_API_KEY, OPENAI_MODEL, LOG_FILE
from utils.logger import get_logger

logger = get_logger()

# Import agents
from agents.note_agent import NoteAgent
from agents.calendar_agent import CalendarAgent
from agents.web_agent import WebAgent
from agents.fallback_agent import FallbackAgent

# Import MCP tools
from mcp.tools import notes, http_fetcher, notion_calendar, notion_notes

console = Console()

# Global instances
_mcp_client = None
_llm_client = None
_agent_instances = {}


def initialize_app():
    """Initialize MCP client, LLM client, and register agents/tools"""
    global _mcp_client, _llm_client, _agent_instances
    
    logger.info("Initializing AI Personal Assistant...")
    
    # Initialize MCP client
    _mcp_client = get_mcp_client()
    logger.debug("MCP client initialized")
    
    # Register MCP tools
    register_tool("notes", notes)
    register_tool("http_fetcher", http_fetcher)
    register_tool("notion_calendar", notion_calendar)
    register_tool("notion_notes", notion_notes)
    logger.info("MCP tools registered: notes, http_fetcher, notion_calendar, notion_notes")
    
    # Initialize LLM client
    _llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    logger.debug(f"LLM client initialized with model: {OPENAI_MODEL}")
    
    # Create agent instances with MCP and LLM clients
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
    logger.info("Initialization complete")


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
        # Fallback to simple response if LLM fails
        return f"작업이 완료되었습니다. 결과: {result.get('result')}"


async def run_once(text: str) -> str:
    """
    Process a single user request
    
    Args:
        text: User input text
        
    Returns:
        Response string
    """
    try:
        logger.info(f"Processing request: {text}")
        
        # Step 1: Parse request
        parsed = await parse_request(text)
        logger.debug(f"Parsed request - Intent: {parsed.intent}, Agent: {parsed.agent}, Params: {parsed.params}")
        
        # Step 2: Route to agent
        agent_class = route_to_agent(parsed)
        
        if agent_class is None:
            logger.warning("No agent found for request")
            return "죄송합니다. 요청을 처리할 수 없습니다."
        
        # Get agent instance
        agent = _agent_instances.get(parsed.agent)
        
        if agent is None:
            # Fallback to FallbackAgent
            logger.warning(f"Agent {parsed.agent} not found, using FallbackAgent")
            agent = _agent_instances.get("FallbackAgent")
        
        logger.info(f"Routing to agent: {agent.get_agent_name()}")
        
        # Step 3: Execute agent
        # Add intent to params for agent to use
        params_with_intent = {**parsed.params, "intent": parsed.intent}
        result = await agent.handle(params_with_intent)
        logger.debug(f"Agent result: {result.get('status')} - {result.get('message', '')}")
        
        # Step 4: Generate natural language response
        final_response = await summarize_result(result, parsed)
        logger.info("Request processed successfully")
        
        return final_response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return f"오류가 발생했습니다: {str(e)}"


async def main_loop():
    """Main interactive loop"""
    # Initialize app
    initialize_app()
    
    console.print(Panel.fit(
        "[bold cyan]AI Personal Assistant[/bold cyan]\n"
        "자연어로 명령을 입력하세요.\n"
        "종료: /exit, 도움말: /help, 디버그: /debug",
        border_style="cyan"
    ))
    
    debug_mode = False
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.strip() == "/exit":
                logger.info("User requested exit")
                console.print("[yellow]종료합니다.[/yellow]")
                break
            elif user_input.strip() == "/help":
                console.print(Panel(
                    "[bold]사용 가능한 명령:[/bold]\n\n"
                    "• 파일 관리: 'downloads 폴더 파일 보여줘'\n"
                    "• 메모: '오늘 한 일 메모해줘: 프로젝트 완료'\n"
                    "• 일정: '오늘 오전 9시에 회의 추가해줘'\n"
                    "• 웹 검색: '파이썬 최신 뉴스 검색해줘'\n\n"
                    "[bold]특수 명령:[/bold]\n"
                    "• /exit - 종료\n"
                    "• /help - 도움말\n"
                    "• /debug - 디버그 모드 토글",
                    title="도움말",
                    border_style="blue"
                ))
                continue
            elif user_input.strip() == "/debug":
                debug_mode = not debug_mode
                status = "활성화" if debug_mode else "비활성화"
                console.print(f"[yellow]디버그 모드 {status}[/yellow]")
                logger.info(f"Debug mode toggled: {debug_mode}")
                continue
            
            # Process request
            response = await run_once(user_input)
            console.print(f"[bold blue]Assistant[/bold blue]: {response}")
            
            # Show debug info if enabled
            if debug_mode:
                console.print(f"[dim]로그 파일: {LOG_FILE}[/dim]")
            
        except KeyboardInterrupt:
            logger.info("User interrupted with Ctrl+C")
            console.print("\n[yellow]종료합니다.[/yellow]")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {str(e)}", exc_info=True)
            console.print(f"[red]Error: {str(e)}[/red]")


def main():
    """Entry point"""
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
