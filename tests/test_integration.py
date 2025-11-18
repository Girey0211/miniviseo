"""
Integration tests for E2E flow
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import initialize_app, run_once


@pytest.fixture(scope="module")
def setup_app():
    """Initialize app once for all tests"""
    initialize_app()


@pytest.mark.asyncio
async def test_list_files_integration(setup_app):
    """Test: downloads 폴더 파일 보여줘"""
    response = await run_once("downloads 폴더 파일 보여줘")
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_write_note_integration(setup_app):
    """Test: 오늘 한 일 메모해줘: Phase 3 완료"""
    response = await run_once("오늘 한 일 메모해줘: Phase 3 완료")
    
    assert response is not None
    assert isinstance(response, str)
    assert "메모" in response or "저장" in response or "완료" in response


@pytest.mark.asyncio
async def test_list_notes_integration(setup_app):
    """Test: notes 전체 알려줘"""
    response = await run_once("notes 전체 알려줘")
    
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_calendar_list_integration(setup_app):
    """Test: calendar 이번주 일정 알려줘"""
    response = await run_once("calendar 이번주 일정 알려줘")
    
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_calendar_add_integration(setup_app):
    """Test: 오늘 오전 9시에 스탠드업 회의 추가해줘"""
    response = await run_once("오늘 오전 9시에 스탠드업 회의 추가해줘")
    
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_web_search_integration(setup_app):
    """Test: 파이썬 최신 뉴스 검색해줘"""
    response = await run_once("파이썬 최신 뉴스 검색해줘")
    
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_unknown_intent_integration(setup_app):
    """Test: Unknown intent handling"""
    response = await run_once("이건 뭔가 이상한 요청이야")
    
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_error_handling_integration(setup_app):
    """Test: Error handling in integration"""
    response = await run_once("")
    
    assert response is not None
    assert isinstance(response, str)
