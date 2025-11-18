"""
Test script to run 10 sample sentences
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import initialize_app, run_once
from rich.console import Console
from rich.panel import Panel

console = Console()

SAMPLE_SENTENCES = [
    "downloads 폴더 파일 보여줘",
    "documents에서 report.pdf 열어줘",
    "오늘 오전 9시에 스탠드업 회의 추가해줘",
    "오늘 한 일 메모해줘: 오늘은 X 작업",
    "파이썬 최신 뉴스 검색해줘",
    "notes 전체 알려줘",
    "calendar 이번주 일정 알려줘",
    "내일 오후 2시 팀 미팅 추가",
    "현재 디렉토리 파일 목록",
    "메모 작성: 프로젝트 Phase 2 완료",
]


async def test_all_samples():
    """Test all 10 sample sentences"""
    console.print(Panel.fit(
        "[bold cyan]10개 샘플 문장 테스트[/bold cyan]\n"
        "각 문장을 실행하고 응답을 확인합니다.",
        border_style="cyan"
    ))
    
    # Initialize app
    initialize_app()
    
    results = []
    
    for i, sentence in enumerate(SAMPLE_SENTENCES, 1):
        console.print(f"\n[bold yellow]테스트 {i}/10[/bold yellow]")
        console.print(f"[bold green]입력:[/bold green] {sentence}")
        
        try:
            response = await run_once(sentence)
            console.print(f"[bold blue]응답:[/bold blue] {response}")
            results.append({
                "sentence": sentence,
                "success": True,
                "response": response
            })
        except Exception as e:
            console.print(f"[bold red]오류:[/bold red] {str(e)}")
            results.append({
                "sentence": sentence,
                "success": False,
                "error": str(e)
            })
        
        console.print("[dim]" + "="*80 + "[/dim]")
    
    # Summary
    success_count = sum(1 for r in results if r["success"])
    console.print(f"\n[bold]결과 요약:[/bold]")
    console.print(f"성공: {success_count}/10")
    console.print(f"실패: {10 - success_count}/10")
    
    if success_count == 10:
        console.print("[bold green]✅ 모든 샘플 문장 테스트 통과![/bold green]")
    else:
        console.print("[bold red]❌ 일부 테스트 실패[/bold red]")
        for r in results:
            if not r["success"]:
                console.print(f"  - {r['sentence']}: {r.get('error', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(test_all_samples())
