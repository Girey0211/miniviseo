"""
Test memo error scenario
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from app import initialize_app, run_once


async def test_memo_error():
    """Test memo with numbered list"""
    
    print("=" * 60)
    print("Memo Error Test")
    print("=" * 60)
    
    # Initialize the app
    print("\nInitializing app...")
    initialize_app()
    print("✓ App initialized\n")
    
    # Test the problematic input
    test_input = "메모 작성해줘. 1. 개발하기 2. 밥먹기 3. qa하고 기획안 마무리하기"
    
    print(f"Input: {test_input}\n")
    
    try:
        response = await run_once(test_input)
        print(f"Response: {response}")
        print("\n✓ SUCCESS")
        
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_memo_error())
