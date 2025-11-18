import pytest
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.tools import file_manager, notes
from mcp.client import MCPClient, get_mcp_client, register_tool


class TestFileManager:
    """Test cases for file_manager tool"""
    
    @pytest.mark.asyncio
    async def test_list_files_current_directory(self):
        """Test listing files in current directory"""
        result = await file_manager.list_files(".")
        
        assert result["status"] == "ok"
        assert isinstance(result["result"], list)
        assert len(result["result"]) > 0
    
    @pytest.mark.asyncio
    async def test_list_files_nonexistent_path(self):
        """Test listing files in nonexistent directory"""
        result = await file_manager.list_files("/nonexistent/path/xyz")
        
        assert result["status"] == "error"
        assert "does not exist" in result["message"]
    
    @pytest.mark.asyncio
    async def test_list_files_returns_metadata(self):
        """Test that list_files returns file metadata"""
        result = await file_manager.list_files(".")
        
        assert result["status"] == "ok"
        files = result["result"]
        
        if len(files) > 0:
            file_item = files[0]
            assert "name" in file_item
            assert "type" in file_item
            assert "size" in file_item
            assert "path" in file_item
    
    @pytest.mark.asyncio
    async def test_read_file_success(self, tmp_path):
        """Test reading a file successfully"""
        # Create a temporary file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)
        
        result = await file_manager.read_file(str(test_file))
        
        assert result["status"] == "ok"
        assert result["result"]["content"] == test_content
        assert result["result"]["truncated"] is False
    
    @pytest.mark.asyncio
    async def test_read_file_nonexistent(self):
        """Test reading nonexistent file"""
        result = await file_manager.read_file("/nonexistent/file.txt")
        
        assert result["status"] == "error"
        assert "does not exist" in result["message"]
    
    @pytest.mark.asyncio
    async def test_read_file_truncation(self, tmp_path):
        """Test file content truncation for large files"""
        # Create a large file
        test_file = tmp_path / "large.txt"
        large_content = "x" * 20000  # 20KB
        test_file.write_text(large_content)
        
        result = await file_manager.read_file(str(test_file), max_bytes=5000)
        
        assert result["status"] == "ok"
        assert result["result"]["truncated"] is True
        assert len(result["result"]["content"]) == 5000


class TestNotes:
    """Test cases for notes tool"""
    
    @pytest.fixture
    def temp_notes_file(self, tmp_path, monkeypatch):
        """Create temporary notes file for testing"""
        notes_file = tmp_path / "test_notes.json"
        
        # Patch NOTES_FILE in notes module
        import config
        monkeypatch.setattr(config, "NOTES_FILE", notes_file)
        
        # Also need to update the imported NOTES_FILE in notes module
        import mcp.tools.notes as notes_module
        monkeypatch.setattr(notes_module, "NOTES_FILE", notes_file)
        
        return notes_file
    
    @pytest.mark.asyncio
    async def test_write_note(self, temp_notes_file):
        """Test writing a note"""
        result = await notes.write(text="Test note content", title="Test Note")
        
        assert result["status"] == "ok"
        assert result["result"]["text"] == "Test note content"
        assert result["result"]["title"] == "Test Note"
        assert "id" in result["result"]
        assert "timestamp" in result["result"]
    
    @pytest.mark.asyncio
    async def test_write_note_without_title(self, temp_notes_file):
        """Test writing a note without title"""
        result = await notes.write(text="Note without title")
        
        assert result["status"] == "ok"
        assert result["result"]["text"] == "Note without title"
        assert result["result"]["title"] == ""
    
    @pytest.mark.asyncio
    async def test_list_notes_empty(self, temp_notes_file):
        """Test listing notes when none exist"""
        result = await notes.list()
        
        assert result["status"] == "ok"
        assert result["result"] == []
        assert "No notes" in result["message"]
    
    @pytest.mark.asyncio
    async def test_list_notes_with_data(self, temp_notes_file):
        """Test listing notes after writing some"""
        # Write some notes
        await notes.write(text="First note", title="Note 1")
        await notes.write(text="Second note", title="Note 2")
        
        result = await notes.list()
        
        assert result["status"] == "ok"
        assert len(result["result"]) == 2
        assert result["result"][0]["text"] == "First note"
        assert result["result"][1]["text"] == "Second note"
    
    @pytest.mark.asyncio
    async def test_notes_persistence(self, temp_notes_file):
        """Test that notes are persisted to file"""
        await notes.write(text="Persistent note", title="Test")
        
        # Check file exists and contains data
        assert temp_notes_file.exists()
        
        with open(temp_notes_file, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["text"] == "Persistent note"


class TestMCPClient:
    """Test cases for MCP Client"""
    
    @pytest.fixture
    def mcp_client(self):
        """Create fresh MCP client for testing"""
        return MCPClient()
    
    def test_register_tool(self, mcp_client):
        """Test registering a tool"""
        mock_tool = "mock_tool_module"
        mcp_client.register_tool("test_tool", mock_tool)
        
        assert "test_tool" in mcp_client.tools
        assert mcp_client.tools["test_tool"] == mock_tool
    
    @pytest.mark.asyncio
    async def test_call_nonexistent_tool(self, mcp_client):
        """Test calling a tool that doesn't exist"""
        result = await mcp_client.call("nonexistent", "action", {})
        
        assert result["status"] == "error"
        assert "not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_call_nonexistent_action(self, mcp_client):
        """Test calling an action that doesn't exist"""
        mcp_client.register_tool("test_tool", file_manager)
        result = await mcp_client.call("test_tool", "nonexistent_action", {})
        
        assert result["status"] == "error"
        assert "not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_call_successful(self, mcp_client):
        """Test successful tool call"""
        mcp_client.register_tool("file_manager", file_manager)
        result = await mcp_client.call("file_manager", "list_files", {"path": "."})
        
        assert result["status"] == "ok"
        assert isinstance(result["result"], list)
    
    def test_get_mcp_client(self):
        """Test getting global MCP client"""
        client = get_mcp_client()
        assert isinstance(client, MCPClient)
    
    def test_register_tool_convenience(self):
        """Test convenience function for registering tool"""
        register_tool("test_tool", file_manager)
        client = get_mcp_client()
        assert "test_tool" in client.tools



class TestCalendarMock:
    """Test cases for calendar_mock tool"""
    
    @pytest.fixture
    def temp_calendar_file(self, tmp_path, monkeypatch):
        """Create temporary calendar file for testing"""
        calendar_file = tmp_path / "test_calendar.json"
        
        # Patch CALENDAR_FILE
        import config
        monkeypatch.setattr(config, "CALENDAR_FILE", calendar_file)
        
        import mcp.tools.calendar_mock as calendar_module
        monkeypatch.setattr(calendar_module, "CALENDAR_FILE", calendar_file)
        
        return calendar_file
    
    @pytest.mark.asyncio
    async def test_add_event(self, temp_calendar_file):
        """Test adding a calendar event"""
        from mcp.tools import calendar_mock
        
        result = await calendar_mock.add_event(
            title="Meeting",
            date="2024-01-01",
            time="09:00",
            description="Team meeting"
        )
        
        assert result["status"] == "ok"
        assert result["result"]["title"] == "Meeting"
        assert result["result"]["date"] == "2024-01-01"
        assert result["result"]["time"] == "09:00"
        assert "id" in result["result"]
    
    @pytest.mark.asyncio
    async def test_add_event_with_relative_date(self, temp_calendar_file):
        """Test adding event with relative date"""
        from mcp.tools import calendar_mock
        
        result = await calendar_mock.add_event(title="Today's meeting", date="오늘", time="10:00")
        
        assert result["status"] == "ok"
        # Should convert "오늘" to actual date
        assert result["result"]["date"] != "오늘"
    
    @pytest.mark.asyncio
    async def test_list_events_empty(self, temp_calendar_file):
        """Test listing events when none exist"""
        from mcp.tools import calendar_mock
        
        result = await calendar_mock.list_events()
        
        assert result["status"] == "ok"
        assert result["result"] == []
    
    @pytest.mark.asyncio
    async def test_list_events_with_data(self, temp_calendar_file):
        """Test listing events after adding some"""
        from mcp.tools import calendar_mock
        
        await calendar_mock.add_event(title="Event 1", date="2024-01-01")
        await calendar_mock.add_event(title="Event 2", date="2024-01-02")
        
        result = await calendar_mock.list_events()
        
        assert result["status"] == "ok"
        assert len(result["result"]) == 2
    
    @pytest.mark.asyncio
    async def test_list_events_with_date_filter(self, temp_calendar_file):
        """Test listing events with date range filter"""
        from mcp.tools import calendar_mock
        
        await calendar_mock.add_event(title="Event 1", date="2024-01-01")
        await calendar_mock.add_event(title="Event 2", date="2024-01-15")
        await calendar_mock.add_event(title="Event 3", date="2024-02-01")
        
        result = await calendar_mock.list_events(range_start="2024-01-10", range_end="2024-01-20")
        
        assert result["status"] == "ok"
        assert len(result["result"]) == 1
        assert result["result"][0]["title"] == "Event 2"


class TestHttpFetcher:
    """Test cases for http_fetcher tool"""
    
    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """Test successful HTTP fetch"""
        from mcp.tools import http_fetcher
        
        # Use a reliable test URL
        result = await http_fetcher.fetch("https://httpbin.org/get")
        
        assert result["status"] == "ok"
        assert result["result"]["status_code"] == 200
        assert "text" in result["result"]
    
    @pytest.mark.asyncio
    async def test_fetch_invalid_url(self):
        """Test fetching invalid URL"""
        from mcp.tools import http_fetcher
        
        result = await http_fetcher.fetch("https://this-domain-does-not-exist-12345.com")
        
        assert result["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """Test fetch with timeout"""
        from mcp.tools import http_fetcher
        
        # Use a URL that will timeout (very short timeout)
        result = await http_fetcher.fetch("https://httpbin.org/delay/10", timeout=1)
        
        assert result["status"] == "error"
        assert "timeout" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_fetch_truncates_large_response(self):
        """Test that large responses are truncated"""
        from mcp.tools import http_fetcher
        
        # httpbin can return large responses
        result = await http_fetcher.fetch("https://httpbin.org/base64/SFRUUEJJTiBpcyBhd2Vzb21l" * 1000)
        
        if result["status"] == "ok":
            assert "truncated" in result["result"]
