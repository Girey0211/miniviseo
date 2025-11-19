import pytest
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.tools import notes
from mcp.client import MCPClient, get_mcp_client, register_tool


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
        mcp_client.register_tool("test_tool", notes)
        result = await mcp_client.call("test_tool", "nonexistent_action", {})
        
        assert result["status"] == "error"
        assert "not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_call_successful(self, mcp_client, tmp_path, monkeypatch):
        """Test successful tool call"""
        # Setup temp notes file
        notes_file = tmp_path / "test_notes.json"
        import config
        monkeypatch.setattr(config, "NOTES_FILE", notes_file)
        import mcp.tools.notes as notes_module
        monkeypatch.setattr(notes_module, "NOTES_FILE", notes_file)
        
        mcp_client.register_tool("notes", notes)
        result = await mcp_client.call("notes", "list", {})
        
        assert result["status"] == "ok"
        assert isinstance(result["result"], list)
    
    def test_get_mcp_client(self):
        """Test getting global MCP client"""
        client = get_mcp_client()
        assert isinstance(client, MCPClient)
    
    def test_register_tool_convenience(self):
        """Test convenience function for registering tool"""
        register_tool("test_tool", notes)
        client = get_mcp_client()
        assert "test_tool" in client.tools



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
    
    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test web search functionality"""
        from mcp.tools import http_fetcher
        
        result = await http_fetcher.search("Python programming", max_results=3)
        
        assert result["status"] == "ok"
        assert isinstance(result["result"], list)
        assert len(result["result"]) <= 3
        
        if len(result["result"]) > 0:
            first_result = result["result"][0]
            assert "title" in first_result
            assert "url" in first_result
            assert "snippet" in first_result
    
    @pytest.mark.asyncio
    async def test_fetch_and_extract_success(self):
        """Test fetching and extracting text from URL"""
        from mcp.tools import http_fetcher
        
        result = await http_fetcher.fetch_and_extract("https://httpbin.org/html")
        
        assert result["status"] == "ok"
        assert "text" in result["result"]
        assert "url" in result["result"]
        assert result["result"]["url"] == "https://httpbin.org/html"
    
    @pytest.mark.asyncio
    async def test_fetch_and_extract_with_max_length(self):
        """Test text extraction respects max_length"""
        from mcp.tools import http_fetcher
        
        result = await http_fetcher.fetch_and_extract("https://httpbin.org/html", max_length=100)
        
        if result["status"] == "ok":
            assert len(result["result"]["text"]) <= 100
