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
from parser.request_parser import parse_request

console = Console()


async def run_once(text: str) -> str:
    """
    Process a single user request
    
    Args:
        text: User input text
        
    Returns:
        Response string
    """
    try:
        # Parse request
        parsed = await parse_request(text)
        
        # For now, just return the parsed result
        return f"[Parsed] Intent: {parsed.intent}, Agent: {parsed.agent}, Params: {parsed.params}"
        
    except Exception as e:
        return f"[Error] {str(e)}"


async def main_loop():
    """Main interactive loop"""
    console.print(Panel.fit(
        "[bold cyan]AI Personal Assistant[/bold cyan]\n"
        "자연어로 명령을 입력하세요.\n"
        "종료: /exit, 도움말: /help",
        border_style="cyan"
    ))
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.strip() == "/exit":
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
                    "• /help - 도움말",
                    title="도움말",
                    border_style="blue"
                ))
                continue
            
            # Process request
            response = await run_once(user_input)
            console.print(f"[bold blue]Assistant[/bold blue]: {response}")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]종료합니다.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")


def main():
    """Entry point"""
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
