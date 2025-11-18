import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestNotionCalendar:
    """Test cases for notion_calendar tool"""
    
    @pytest.mark.asyncio
    async def test_list_events_without_config(self, monkeypatch):
        """Test listing events without Notion configuration"""
        # Clear environment variables
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        
        # Reimport to pick up env changes
        import importlib
        from mcp.tools import notion_calendar
        importlib.reload(notion_calendar)
        
        result = await notion_calendar.list_events()
        
        assert result["status"] == "error"
        assert "not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_add_event_without_config(self, monkeypatch):
        """Test adding event without Notion configuration"""
        # Clear environment variables
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
        
        # Reimport to pick up env changes
        import importlib
        from mcp.tools import notion_calendar
        importlib.reload(notion_calendar)
        
        result = await notion_calendar.add_event(title="Test Event")
        
        assert result["status"] == "error"
        assert "not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_add_event_with_mock_notion(self, monkeypatch):
        """Test adding event with mocked Notion client"""
        # Set environment variables
        monkeypatch.setenv("NOTION_API_KEY", "secret_test_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_database_id")
        
        # Mock AsyncClient
        mock_client = MagicMock()
        mock_client.pages.create = AsyncMock(return_value={
            "id": "test_page_id",
            "url": "https://notion.so/test",
            "created_time": "2024-01-01T00:00:00.000Z"
        })
        
        # Patch both AsyncClient and environment variables in the module
        with patch('mcp.tools.notion_calendar.AsyncClient', return_value=mock_client), \
             patch('mcp.tools.notion_calendar.NOTION_API_KEY', "secret_test_key"), \
             patch('mcp.tools.notion_calendar.NOTION_DATABASE_ID', "test_database_id"):
            
            from mcp.tools import notion_calendar
            
            result = await notion_calendar.add_event(
                title="Test Meeting",
                date="2024-01-01",
                time="09:00",
                description="Test description"
            )
            
            assert result["status"] == "ok"
            assert result["result"]["title"] == "Test Meeting"
            assert result["result"]["date"] == "2024-01-01"
            assert result["result"]["time"] == "09:00"
    
    @pytest.mark.asyncio
    async def test_list_events_with_mock_notion(self, monkeypatch):
        """Test listing events with mocked Notion client"""
        # Set environment variables
        monkeypatch.setenv("NOTION_API_KEY", "secret_test_key")
        monkeypatch.setenv("NOTION_DATABASE_ID", "test_database_id")
        
        # Mock AsyncClient
        mock_client = MagicMock()
        mock_client.databases.query = AsyncMock(return_value={
            "results": [
                {
                    "id": "page1",
                    "url": "https://notion.so/page1",
                    "properties": {
                        "Name": {
                            "title": [{"plain_text": "Event 1"}]
                        },
                        "Date": {
                            "date": {"start": "2024-01-01"}
                        }
                    }
                }
            ]
        })
        
        # Patch both AsyncClient and environment variables in the module
        with patch('mcp.tools.notion_calendar.AsyncClient', return_value=mock_client), \
             patch('mcp.tools.notion_calendar.NOTION_API_KEY', "secret_test_key"), \
             patch('mcp.tools.notion_calendar.NOTION_DATABASE_ID', "test_database_id"):
            
            from mcp.tools import notion_calendar
            
            result = await notion_calendar.list_events()
            
            assert result["status"] == "ok"
            assert len(result["result"]) == 1
            assert result["result"][0]["title"] == "Event 1"
    
    def test_parse_relative_date(self):
        """Test parsing relative date strings"""
        from mcp.tools.notion_calendar import _parse_relative_date
        from datetime import datetime
        
        # Test "오늘"
        today = _parse_relative_date("오늘")
        assert today == datetime.now().strftime("%Y-%m-%d")
        
        # Test "today"
        today = _parse_relative_date("today")
        assert today == datetime.now().strftime("%Y-%m-%d")
        
        # Test absolute date
        date = _parse_relative_date("2024-01-01")
        assert date == "2024-01-01"


class TestCalendarAgentWithNotion:
    """Test CalendarAgent with Notion integration"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_calendar_agent_fallback_to_mock(self, mock_mcp):
        """Test CalendarAgent falls back to mock when Notion not configured"""
        from agents.calendar_agent import CalendarAgent
        
        # First call returns Notion error
        # Second call returns mock success
        mock_mcp.call.side_effect = [
            {
                "status": "error",
                "result": None,
                "message": "Notion API key or database ID not configured"
            },
            {
                "status": "ok",
                "result": {"id": 1, "title": "Test Event"},
                "message": "Event added"
            }
        ]
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        result = await agent.handle({
            "action": "add",
            "title": "Test Event",
            "date": "2024-01-01"
        })
        
        # Should succeed with mock fallback
        assert result["status"] == "ok"
        # Should have called twice (Notion then mock)
        assert mock_mcp.call.call_count == 2
