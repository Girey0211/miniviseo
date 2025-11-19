"""
Integration tests for multi-action support with context passing
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.note_agent import NoteAgent
from agents.calendar_agent import CalendarAgent
from agents.web_agent import WebAgent


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client"""
    client = MagicMock()
    client.call = AsyncMock()
    return client


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client"""
    return MagicMock()


class TestMultiActionContextPassing:
    """Test context passing between actions"""
    
    @pytest.mark.asyncio
    async def test_web_search_to_note(self, mock_mcp_client, mock_llm_client):
        """Test web search result being used in note creation"""
        # Setup web agent
        web_agent = WebAgent(mcp_client=mock_mcp_client)
        
        # Mock search and fetch operations
        mock_mcp_client.call.side_effect = [
            # First call: search
            {
                "status": "ok",
                "result": [
                    {"title": "부산집", "url": "http://example.com/1"},
                    {"title": "해운대식당", "url": "http://example.com/2"}
                ]
            },
            # Second call: fetch first result
            {
                "status": "ok",
                "result": {"text": "부산집 - 돼지국밥 전문점"}
            },
            # Third call: fetch second result
            {
                "status": "ok",
                "result": {"text": "해운대식당 - 회 전문점"}
            }
        ]
        
        # Mock LLM summarization
        search_summary = "부산역 맛집:\n1. 부산집 - 돼지국밥 전문점\n2. 해운대식당 - 회 전문점"
        with patch.object(web_agent, '_summarize_with_llm', return_value=search_summary):
            web_params = {"intent": "web_search", "query": "부산역 맛집"}
            web_result = await web_agent.handle(web_params)
            assert web_result["status"] == "ok"
        
        # Setup note agent with fresh mock
        note_mock_mcp = MagicMock()
        note_mock_mcp.call = AsyncMock()
        note_agent = NoteAgent(mcp_client=note_mock_mcp, llm_client=mock_llm_client)
        
        # Mock title generation
        with patch.object(note_agent, '_generate_title', return_value="부산역 맛집 리스트"):
            # Mock note creation
            note_result = {"status": "ok", "result": "Note created", "message": "Note saved to Notion"}
            note_mock_mcp.call.return_value = note_result
            
            # Execute note creation with previous results
            note_params = {
                "intent": "write_note",
                "previous_results": [
                    {"action": 1, "intent": "web_search", "agent": "WebAgent", "result": web_result}
                ]
            }
            
            result = await note_agent.handle(note_params)
            
            assert result["status"] == "ok"
            # Verify that notion_notes.write was called with the search result including sources
            call_args = note_mock_mcp.call.call_args
            assert call_args[0][0] == "notion_notes"
            assert call_args[0][1] == "write"
            note_data = call_args[0][2]
            assert note_data["title"] == "부산역 맛집 리스트"
            assert search_summary in note_data["text"]
            assert "참고 링크" in note_data["text"]
    
    @pytest.mark.asyncio
    async def test_web_search_to_calendar(self, mock_mcp_client, mock_llm_client):
        """Test web search result being used in calendar event description"""
        # Setup web agent
        web_agent = WebAgent(mcp_client=mock_mcp_client)
        
        # Mock search and fetch operations
        mock_mcp_client.call.side_effect = [
            {"status": "ok", "result": [{"title": "부산집", "url": "http://example.com/1"}]},
            {"status": "ok", "result": {"text": "부산집 - 돼지국밥 전문점"}}
        ]
        
        # Mock LLM summarization
        search_summary = "부산역 맛집:\n1. 부산집 - 돼지국밥 전문점"
        with patch.object(web_agent, '_summarize_with_llm', return_value=search_summary):
            web_params = {"intent": "web_search", "query": "부산역 맛집"}
            web_result = await web_agent.handle(web_params)
            assert web_result["status"] == "ok"
        
        # Setup calendar agent with fresh mock
        calendar_mock_mcp = MagicMock()
        calendar_mock_mcp.call = AsyncMock()
        calendar_agent = CalendarAgent(mcp_client=calendar_mock_mcp, llm_client=mock_llm_client)
        
        # Mock event data extraction
        with patch.object(calendar_agent, '_extract_event_data') as mock_extract:
            mock_extract.return_value = {
                "title": "밥약속",
                "date": "2025-01-02",
                "time": "15:00",
                "description": "내일 3시에 밥약속"
            }
            
            # Mock calendar event creation
            calendar_result = {"status": "ok", "result": "Event created", "message": "Event added to calendar"}
            calendar_mock_mcp.call.return_value = calendar_result
            
            # Execute calendar add with previous results
            calendar_params = {
                "intent": "calendar_add",
                "text": "내일 3시에 밥약속",
                "previous_results": [
                    {"action": 1, "intent": "web_search", "agent": "WebAgent", "result": web_result}
                ]
            }
            
            result = await calendar_agent.handle(calendar_params)
            
            assert result["status"] == "ok"
            # Verify that the calendar event includes search results in description
            call_args = calendar_mock_mcp.call.call_args
            assert call_args[0][0] == "notion_calendar"
            assert call_args[0][1] == "add_event"
            event_data = call_args[0][2]
            assert search_summary in event_data["description"]
    
    @pytest.mark.asyncio
    async def test_note_without_previous_results(self, mock_mcp_client, mock_llm_client):
        """Test note creation without previous results (normal case)"""
        note_agent = NoteAgent(mcp_client=mock_mcp_client, llm_client=mock_llm_client)
        
        # Mock title generation
        with patch.object(note_agent, '_generate_title', return_value="테스트 메모"):
            # Mock note creation
            note_result = {"status": "ok", "result": "Note created", "message": "Note saved"}
            mock_mcp_client.call.return_value = note_result
            
            # Execute note creation without previous results
            note_params = {
                "intent": "write_note",
                "text": "테스트 메모 내용",
                "previous_results": []
            }
            
            result = await note_agent.handle(note_params)
            
            assert result["status"] == "ok"
            # Verify that the provided text was used
            mock_mcp_client.call.assert_called_with(
                "notion_notes", "write",
                {"text": "테스트 메모 내용", "title": "테스트 메모"}
            )
    
    @pytest.mark.asyncio
    async def test_calendar_without_previous_results(self, mock_mcp_client, mock_llm_client):
        """Test calendar event creation without previous results (normal case)"""
        calendar_agent = CalendarAgent(mcp_client=mock_mcp_client, llm_client=mock_llm_client)
        
        # Mock event data extraction
        with patch.object(calendar_agent, '_extract_event_data') as mock_extract:
            mock_extract.return_value = {
                "title": "회의",
                "date": "2025-01-02",
                "time": "09:00",
                "description": "내일 오전 9시 회의"
            }
            
            # Mock calendar event creation
            calendar_result = {"status": "ok", "result": "Event created", "message": "Event added"}
            mock_mcp_client.call.return_value = calendar_result
            
            # Execute calendar add without previous results
            calendar_params = {
                "intent": "calendar_add",
                "text": "내일 오전 9시 회의",
                "previous_results": []
            }
            
            result = await calendar_agent.handle(calendar_params)
            
            assert result["status"] == "ok"
            # Verify that only the provided text was used
            call_args = mock_mcp_client.call.call_args
            event_data = call_args[0][2]
            assert event_data["description"] == "내일 오전 9시 회의"
