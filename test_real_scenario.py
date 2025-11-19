"""
Real scenario test for AI Assistant
Tests the full flow: Parser -> Router -> Agent -> Response
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import initialize_app, run_once


async def test_scenarios():
    """Test various real-world scenarios"""
    
    print("=" * 60)
    print("AI Assistant - Real Scenario Test")
    print("=" * 60)
    
    # Initialize the app
    print("\n[1/5] Initializing app...")
    initialize_app()
    print("✓ App initialized")
    
    # Test scenarios
    scenarios = [
        {
            "name": "메모 작성 (한국어 키워드)",
            "input": "메모 작성해줘: 오늘 프로젝트 리팩토링 완료했음",
            "expected_agent": "NoteAgent"
        },
        {
            "name": "노트 목록 조회",
            "input": "노트 목록 보여줘",
            "expected_agent": "NoteAgent"
        },
        {
            "name": "일정 추가 (자연어)",
            "input": "내일 오후 3시에 팀 회의 잡아줘",
            "expected_agent": "CalendarAgent"
        },
        {
            "name": "일정 조회",
            "input": "이번주 일정 알려줘",
            "expected_agent": "CalendarAgent"
        },
        {
            "name": "기록 남기기 (한국어 키워드)",
            "input": "기록 남겨줘: 버그 수정 완료",
            "expected_agent": "NoteAgent"
        }
    ]
    
    print(f"\n[2/5] Running {len(scenarios)} test scenarios...\n")
    
    results = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Test {i}/{len(scenarios)}: {scenario['name']} ---")
        print(f"Input: {scenario['input']}")
        
        try:
            response = await run_once(scenario['input'])
            print(f"Response: {response}")
            
            # Check if response is not an error
            is_success = "오류" not in response and "Error" not in response
            status = "✓ PASS" if is_success else "✗ FAIL"
            
            results.append({
                "name": scenario['name'],
                "status": status,
                "success": is_success
            })
            
            print(f"Status: {status}")
            
        except Exception as e:
            print(f"✗ FAIL - Exception: {str(e)}")
            results.append({
                "name": scenario['name'],
                "status": "✗ FAIL",
                "success": False
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    
    for result in results:
        print(f"{result['status']} - {result['name']}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(test_scenarios())
    sys.exit(0 if success else 1)
