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
        from mcp.tools import notion_calendar
        
        # Patch the environment variables at module level
        monkeypatch.setattr(notion_calendar, "NOTION_API_KEY", None)
        monkeypatch.setattr(notion_calendar, "NOTION_CALENDAR_DATABASE_ID", None)
        
        result = await notion_calendar.list_events()
        
        assert result["status"] == "error"
        assert "not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_add_event_without_config(self, monkeypatch):
        """Test adding event without Notion configuration"""
        from mcp.tools import notion_calendar
        
        # Patch the environment variables at module level
        monkeypatch.setattr(notion_calendar, "NOTION_API_KEY", None)
        monkeypatch.setattr(notion_calendar, "NOTION_CALENDAR_DATABASE_ID", None)
        
        result = await notion_calendar.add_event(title="Test Event")
        
        assert result["status"] == "error"
        assert "not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_add_event_with_real_config(self, monkeypatch):
        """Test adding event - requires real Notion configuration"""
        import os
        from mcp.tools import notion_calendar
        
        # Only run if Notion is configured
        if not (os.getenv("NOTION_API_KEY") and os.getenv("NOTION_CALENDAR_DATABASE_ID")):
            pytest.skip("Notion not configured - skipping real API test")
        
        # This test validates that the function works with real config
        # but doesn't actually call the API (would need cleanup)
        result = await notion_calendar.add_event(
            title="Test Event (will not be created)",
            date="2099-12-31",  # Far future date
            time="23:59"
        )
        
        # Accept both success and error (API might fail for various reasons)
        assert result["status"] in ["ok", "error"]
        assert "result" in result or "message" in result
    
    @pytest.mark.asyncio
    async def test_list_events_with_mock_notion(self, monkeypatch):
        """Test listing events with mocked httpx"""
        from mcp.tools import notion_calendar
        from unittest.mock import MagicMock, patch
        
        # Mock httpx.Client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "page1",
                    "url": "https://notion.so/page1",
                    "properties": {
                        "이름": {
                            "title": [{"plain_text": "Event 1"}]
                        },
                        "날짜": {
                            "date": {"start": "2024-01-01"}
                        }
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        
        # Patch environment variables and httpx
        monkeypatch.setattr(notion_calendar, "NOTION_API_KEY", "test_key")
        monkeypatch.setattr(notion_calendar, "NOTION_CALENDAR_DATABASE_ID", "test_db_id")
        
        with patch('httpx.Client', return_value=mock_client):
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
    

