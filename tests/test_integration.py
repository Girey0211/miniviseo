"""
Integration tests for E2E flow
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import initialize_app, run_once


@pytest.fixture(scope="module")
async def setup_app():
    """Initialize app once for all tests"""
    await initialize_app()


@pytest.mark.asyncio
async def test_file_intent_routes_to_fallback(setup_app):
    """Test: File-related intents route to FallbackAgent"""
    response = await run_once("downloads 폴더 파일 보여줘")
    
    assert response is not None
    assert isinstance(response, str)
    # Should get fallback response since FileAgent is removed
    # FallbackAgent returns various Korean messages indicating it can't help
    assert any(keyword in response for keyword in ["죄송", "수 없", "도와드릴", "문제"])


@pytest.mark.asyncio
async def test_write_note_notion_integration(setup_app):
    """Test: Notion notes creation E2E flow"""
    with patch('httpx.Client') as mock_client_class:
        # Mock Notion API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test-page-123",
            "url": "https://notion.so/test-page-123",
            "created_time": "2024-01-15T10:30:00.000Z",
            "properties": {
                "제목": {"title": [{"text": {"content": "Test Note"}}]},
                "내용": {"rich_text": [{"text": {"content": "Phase 3 완료"}}]},
                "생성일": {"created_time": "2024-01-15T10:30:00.000Z"}
            }
        }
        
        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_client_instance
        
        response = await run_once("오늘 한 일 메모해줘: Phase 3 완료")
        
        assert response is not None
        assert isinstance(response, str)


@pytest.mark.asyncio
async def test_list_notes_notion_integration(setup_app):
    """Test: Notion notes retrieval E2E flow"""
    with patch('httpx.Client') as mock_client_class:
        # Mock Notion API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "url": "https://notion.so/page-1",
                    "properties": {
                        "제목": {"title": [{"text": {"plain_text": "Note 1"}}]},
                        "내용": {"rich_text": [{"text": {"plain_text": "Content 1"}}]},
                        "생성일": {"created_time": "2024-01-15T10:30:00.000Z"}
                    }
                }
            ]
        }
        
        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_client_instance
        
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


@pytest.mark.asyncio
async def test_sample_sentence_1(setup_app):
    """샘플 문장 1: downloads 폴더 파일 보여줘 (routes to FallbackAgent)"""
    response = await run_once("downloads 폴더 파일 보여줘")
    assert response is not None
    assert isinstance(response, str)
    # File intents now route to FallbackAgent - check for Korean error messages
    assert any(keyword in response for keyword in ["죄송", "수 없", "도와드릴", "문제"])


@pytest.mark.asyncio
async def test_sample_sentence_2(setup_app):
    """샘플 문장 2: documents에서 report.pdf 열어줘 (routes to FallbackAgent)"""
    response = await run_once("documents에서 report.pdf 열어줘")
    assert response is not None
    assert isinstance(response, str)
    # File intents now route to FallbackAgent - check for Korean error messages
    assert any(keyword in response for keyword in ["죄송", "수 없", "도와드릴", "문제"])


@pytest.mark.asyncio
async def test_sample_sentence_3(setup_app):
    """샘플 문장 3: 오늘 오전 9시에 스탠드업 회의 추가해줘"""
    response = await run_once("오늘 오전 9시에 스탠드업 회의 추가해줘")
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_sample_sentence_4(setup_app):
    """샘플 문장 4: 오늘 한 일 메모해줘: 오늘은 X 작업"""
    response = await run_once("오늘 한 일 메모해줘: 오늘은 X 작업")
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_sample_sentence_5(setup_app):
    """샘플 문장 5: 파이썬 최신 뉴스 검색해줘"""
    response = await run_once("파이썬 최신 뉴스 검색해줘")
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_sample_sentence_6(setup_app):
    """샘플 문장 6: notes 전체 알려줘"""
    response = await run_once("notes 전체 알려줘")
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_sample_sentence_7(setup_app):
    """샘플 문장 7: calendar 이번주 일정 알려줘"""
    response = await run_once("calendar 이번주 일정 알려줘")
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_sample_sentence_8(setup_app):
    """샘플 문장 8: 내일 오후 2시 팀 미팅 추가"""
    response = await run_once("내일 오후 2시 팀 미팅 추가")
    assert response is not None
    assert isinstance(response, str)


@pytest.mark.asyncio
async def test_sample_sentence_9(setup_app):
    """샘플 문장 9: 현재 디렉토리 파일 목록 (routes to FallbackAgent)"""
    response = await run_once("현재 디렉토리 파일 목록")
    assert response is not None
    assert isinstance(response, str)
    # File intents now route to FallbackAgent - check for Korean error messages
    assert any(keyword in response for keyword in ["죄송", "수 없", "도와드릴", "문제"])


@pytest.mark.asyncio
async def test_sample_sentence_10(setup_app):
    """샘플 문장 10: 메모 작성: 프로젝트 Phase 2 완료"""
    response = await run_once("메모 작성: 프로젝트 Phase 2 완료")
    assert response is not None
    assert isinstance(response, str)
