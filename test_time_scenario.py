"""
Test time handling in calendar events
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import initialize_app, run_once


async def test_time_scenarios():
    """Test time handling scenarios"""
    
    print("=" * 60)
    print("Calendar Time Test (KST)")
    print("=" * 60)
    
    # Initialize the app
    print("\nInitializing app...")
    initialize_app()
    print("✓ App initialized\n")
    
    # Test scenarios with specific times
    scenarios = [
        {
            "name": "오전 시간 (9시)",
            "input": "내일 오전 9시에 스탠드업 미팅",
            "expected_time": "09:00"
        },
        {
            "name": "오후 시간 (3시)",
            "input": "내일 오후 3시에 팀 회의",
            "expected_time": "15:00"
        },
        {
            "name": "저녁 시간 (7시)",
            "input": "내일 저녁 7시에 저녁 식사",
            "expected_time": "19:00"
        }
    ]
    
    print(f"Running {len(scenarios)} time test scenarios...\n")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Test {i}/{len(scenarios)}: {scenario['name']} ---")
        print(f"Input: {scenario['input']}")
        print(f"Expected time: {scenario['expected_time']} KST")
        
        try:
            response = await run_once(scenario['input'])
            print(f"Response: {response}")
            
            # Check if response indicates success
            is_success = "오류" not in response and "Error" not in response
            status = "✓ PASS" if is_success else "✗ FAIL"
            print(f"Status: {status}")
            
        except Exception as e:
            print(f"✗ FAIL - Exception: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    print("\nPlease check Notion to verify times are correct in KST")


if __name__ == "__main__":
    asyncio.run(test_time_scenarios())
