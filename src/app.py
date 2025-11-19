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
from rich.spinner import Spinner
from rich.live import Live
from openai import AsyncOpenAI

from parser.request_parser import parse_request
from router.agent_router import route_to_agent, register_agent
from mcp.client import get_mcp_client, register_tool
from config import OPENAI_API_KEY, OPENAI_MODEL, LOG_FILE
from utils.logger import get_logger, set_console_level
from session import get_session_manager

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
_session_manager = None
_current_session = None


async def initialize_app():
    """Initialize MCP client, LLM client, session manager, and register agents/tools"""
    global _mcp_client, _llm_client, _agent_instances, _session_manager, _current_session
    
    logger.info("Initializing AI Personal Assistant...")
    
    # Initialize session manager
    _session_manager = get_session_manager()
    logger.debug("Session manager initialized")
    
    # Create or restore CLI session
    import uuid
    import os
    session_file = Path.home() / ".ai-assistant-session"
    
    if session_file.exists():
        session_id = session_file.read_text().strip()
        logger.debug(f"Restoring session: {session_id}")
    else:
        session_id = f"cli-{uuid.uuid4().hex[:8]}"
        session_file.write_text(session_id)
        logger.debug(f"Created new session: {session_id}")
    
    _current_session = await _session_manager.get_or_create_session(session_id)
    message_count = await _current_session.get_message_count()
    logger.info(f"Session loaded: {session_id} ({message_count} messages)")
    
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
        # Fallback to simple response if LLM fails
        logger.error(f"Error in summarize_result: {str(e)}")
        return f"작업이 완료되었습니다. 결과: {result.get('result')}"


async def run_once(text: str) -> str:
    """
    Process a single user request with conversation history
    
    Args:
        text: User input text
        
    Returns:
        Response string
    """
    try:
        logger.info(f"Processing request: {text}")
        
        # Add user message to session
        await _current_session.add_message("user", text)
        
        # Get conversation context for LLM
        conversation_history = await _current_session.get_context_for_llm(limit=10)
        
        # Step 1: Parse request
        parsed = await parse_request(text)
        logger.debug(f"Parsed request - Intent: {parsed.intent}, Agent: {parsed.agent}, Params: {parsed.params}")
        
        # Step 2: Route to agent
        agent_class = route_to_agent(parsed)
        
        if agent_class is None:
            logger.warning("No agent found for request")
            response = "죄송합니다. 요청을 처리할 수 없습니다."
            await _current_session.add_message("assistant", response)
            return response
        
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
        
        # Step 4: Generate natural language response with conversation history
        final_response = await summarize_result(result, parsed, conversation_history)
        logger.info("Request processed successfully")
        
        # Add assistant response to session
        await _current_session.add_message(
            "assistant",
            final_response,
            metadata={
                "intent": parsed.intent,
                "agent": parsed.agent,
                "status": result.get("status", "ok")
            }
        )
        
        return final_response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        error_response = f"오류가 발생했습니다: {str(e)}"
        await _current_session.add_message("assistant", error_response)
        return error_response


async def main_loop():
    """Main interactive loop"""
    # Initialize app
    await initialize_app()
    
    console.print(Panel.fit(
        "[bold cyan]AI Personal Assistant[/bold cyan]\n"
        "자연어로 명령을 입력하세요. 도움말: [bold]/help[/bold]",
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
                message_count = await _current_session.get_message_count()
                session_info = f"세션: {_current_session.session_id} ({message_count}개 메시지)" if message_count > 0 else f"세션: {_current_session.session_id} (새 세션)"
                
                console.print(Panel(
                    f"[bold cyan]세션 정보[/bold cyan]\n"
                    f"{session_info}\n\n"
                    "[bold cyan]사용 가능한 명령[/bold cyan]\n\n"
                    "[bold]자연어 요청:[/bold]\n"
                    "• 메모: '오늘 한 일 메모해줘: 프로젝트 완료'\n"
                    "• 일정: '오늘 오전 9시에 회의 추가해줘'\n"
                    "• 웹 검색: '파이썬 최신 뉴스 검색해줘'\n\n"
                    "[bold]특수 명령:[/bold]\n"
                    "• [bold]/help[/bold] - 이 도움말 보기\n"
                    "• [bold]/history[/bold] - 대화 히스토리 보기 (최근 10개)\n"
                    "• [bold]/clear[/bold] - 대화 히스토리 초기화\n"
                    "• [bold]/debug[/bold] - 디버그 모드 토글\n"
                    "• [bold]/exit[/bold] - 종료",
                    title="AI Personal Assistant - 도움말",
                    border_style="cyan"
                ))
                continue
            elif user_input.strip() == "/clear":
                await _current_session.clear()
                console.print("[yellow]대화 히스토리가 초기화되었습니다.[/yellow]")
                logger.info("Conversation history cleared")
                continue
            elif user_input.strip() == "/history":
                messages = await _current_session.get_messages(page=0, page_size=20)
                if not messages:
                    console.print("[yellow]대화 히스토리가 없습니다.[/yellow]")
                else:
                    console.print(Panel(
                        "\n".join([
                            f"[{'green' if msg['role'] == 'user' else 'blue'}]{msg['role']}[/]: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}"
                            for msg in messages[-10:]  # Show last 10 messages
                        ]),
                        title=f"대화 히스토리 (최근 10개, 전체 {len(messages)}개)",
                        border_style="blue"
                    ))
                continue
            elif user_input.strip() == "/debug":
                debug_mode = not debug_mode
                status = "활성화" if debug_mode else "비활성화"
                
                # Change console log level based on debug mode
                if debug_mode:
                    set_console_level("INFO")
                else:
                    set_console_level("WARNING")
                
                console.print(f"[yellow]디버그 모드 {status}[/yellow]")
                logger.info(f"Debug mode toggled: {debug_mode}")
                continue
            
            # Process request with spinner
            with console.status("[cyan]처리 중...", spinner="line") as status:
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
