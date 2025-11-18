"""
Test calendar sample sentences
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import initialize_app, run_once
from rich.console import Console

console = Console()

async def test_calendar_samples():
    """Test calendar sample sentences"""
    console.print("[bold cyan]캘린더 샘플 문장 테스트[/bold cyan]\n")
    
    # Initialize app
    initialize_app()
    
    # Test 1
    console.print("[bold yellow]테스트 1:[/bold yellow]")
    console.print("[bold green]입력:[/bold green] calendar 이번주 일정 알려줘")
    response1 = await run_once("calendar 이번주 일정 알려줘")
    console.print(f"[bold blue]응답:[/bold blue] {response1}\n")
    
    # Test 2
    console.print("[bold yellow]테스트 2:[/bold yellow]")
    console.print("[bold green]입력:[/bold green] 내일 오후 2시 팀 미팅 추가")
    response2 = await run_once("내일 오후 2시 팀 미팅 추가")
    console.print(f"[bold blue]응답:[/bold blue] {response2}\n")
    
    console.print("[bold green]✅ 테스트 완료[/bold green]")

if __name__ == "__main__":
    asyncio.run(test_calendar_samples())
