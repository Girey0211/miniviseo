import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base import AgentBase
from agents.file_agent import FileAgent
from agents.note_agent import NoteAgent


# Concrete implementation for testing
class TestAgent(AgentBase):
    """Test agent implementation"""
    
    async def handle(self, params):
        """Test implementation of handle"""
        return self._create_success_response(
            result={"test": "data"},
            message="Test successful"
        )


class TestAgentBase:
    """Test cases for AgentBase"""
    
    def test_agent_initialization(self):
        """Test agent can be initialized"""
        agent = TestAgent()
        assert agent.mcp is None
        assert agent.llm is None
    
    def test_agent_initialization_with_clients(self):
        """Test agent initialization with clients"""
        mock_mcp = "mock_mcp_client"
        mock_llm = "mock_llm_client"
        
        agent = TestAgent(mcp_client=mock_mcp, llm_client=mock_llm)
        assert agent.mcp == mock_mcp
        assert agent.llm == mock_llm
    
    @pytest.mark.asyncio
    async def test_handle_method_must_be_implemented(self):
        """Test that handle method must be implemented"""
        
        class IncompleteAgent(AgentBase):
            pass
        
        with pytest.raises(TypeError):
            agent = IncompleteAgent()
    
    @pytest.mark.asyncio
    async def test_handle_returns_dict(self):
        """Test that handle returns a dictionary"""
        agent = TestAgent()
        result = await agent.handle({})
        
        assert isinstance(result, dict)
        assert "status" in result
        assert "result" in result
    
    def test_create_success_response(self):
        """Test creating success response"""
        agent = TestAgent()
        response = agent._create_success_response(
            result={"data": "test"},
            message="Success"
        )
        
        assert response["status"] == "ok"
        assert response["result"] == {"data": "test"}
        assert response["message"] == "Success"
    
    def test_create_success_response_without_message(self):
        """Test creating success response without message"""
        agent = TestAgent()
        response = agent._create_success_response(result="test_data")
        
        assert response["status"] == "ok"
        assert response["result"] == "test_data"
        assert response["message"] == ""
    
    def test_create_error_response(self):
        """Test creating error response"""
        agent = TestAgent()
        response = agent._create_error_response(message="Test error")
        
        assert response["status"] == "error"
        assert response["result"] is None
        assert response["message"] == "Test error"
    
    def test_create_error_response_with_exception(self):
        """Test creating error response with exception"""
        agent = TestAgent()
        test_error = ValueError("Test exception")
        response = agent._create_error_response(
            message="Error occurred",
            error=test_error
        )
        
        assert response["status"] == "error"
        assert response["message"] == "Error occurred"
        assert "error_detail" in response
        assert "Test exception" in response["error_detail"]
    
    def test_get_agent_name(self):
        """Test getting agent name"""
        agent = TestAgent()
        assert agent.get_agent_name() == "TestAgent"
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_without_client(self):
        """Test respond_via_llm without LLM client"""
        agent = TestAgent()
        response = await agent.respond_via_llm("test prompt")
        
        assert response == "LLM client not available"
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_with_client(self):
        """Test respond_via_llm with LLM client"""
        agent = TestAgent(llm_client="mock_llm")
        response = await agent.respond_via_llm("test prompt")
        
        # Should return placeholder for now
        assert "Response for:" in response
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_with_context(self):
        """Test respond_via_llm with context"""
        agent = TestAgent(llm_client="mock_llm")
        context = {"key": "value"}
        response = await agent.respond_via_llm("test prompt", context=context)
        
        assert isinstance(response, str)


class TestAgentBaseAbstract:
    """Test abstract nature of AgentBase"""
    
    def test_cannot_instantiate_base_directly(self):
        """Test that AgentBase cannot be instantiated directly"""
        with pytest.raises(TypeError):
            agent = AgentBase()
    
    def test_subclass_must_implement_handle(self):
        """Test that subclass must implement handle method"""
        
        class BadAgent(AgentBase):
            """Agent without handle implementation"""
            pass
        
        with pytest.raises(TypeError):
            agent = BadAgent()
    
    @pytest.mark.asyncio
    async def test_valid_subclass_can_be_instantiated(self):
        """Test that valid subclass can be instantiated"""
        
        class GoodAgent(AgentBase):
            async def handle(self, params):
                return {"status": "ok", "result": None}
        
        agent = GoodAgent()
        assert isinstance(agent, AgentBase)
        result = await agent.handle({})
        assert result["status"] == "ok"



class TestFileAgent:
    """Test cases for FileAgent"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_file_agent_list_files(self, mock_mcp):
        """Test FileAgent listing files"""
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": [{"name": "test.txt", "type": "file"}],
            "message": "Found 1 items"
        }
        
        agent = FileAgent(mcp_client=mock_mcp)
        result = await agent.handle({"path": ".", "action": "list_files"})
        
        assert result["status"] == "ok"
        assert len(result["result"]) == 1
        mock_mcp.call.assert_called_once_with("file_manager", "list_files", {"path": "."})
    
    @pytest.mark.asyncio
    async def test_file_agent_read_file(self, mock_mcp):
        """Test FileAgent reading a file"""
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {"content": "file content"},
            "message": "File read"
        }
        
        agent = FileAgent(mcp_client=mock_mcp)
        result = await agent.handle({"path": "test.txt", "action": "read_file"})
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once_with("file_manager", "read_file", {"path": "test.txt"})
    
    @pytest.mark.asyncio
    async def test_file_agent_without_mcp(self):
        """Test FileAgent without MCP client"""
        agent = FileAgent()
        result = await agent.handle({"path": "."})
        
        assert result["status"] == "error"
        assert "MCP client not available" in result["message"]
    
    @pytest.mark.asyncio
    async def test_file_agent_default_path(self, mock_mcp):
        """Test FileAgent with default path"""
        mock_mcp.call.return_value = {"status": "ok", "result": [], "message": ""}
        
        agent = FileAgent(mcp_client=mock_mcp)
        result = await agent.handle({})
        
        # Should use default path "."
        mock_mcp.call.assert_called_once()
        call_args = mock_mcp.call.call_args
        assert call_args[0][2]["path"] == "."


class TestNoteAgent:
    """Test cases for NoteAgent"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_note_agent_write_note(self, mock_mcp):
        """Test NoteAgent writing a note"""
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {"id": 1, "text": "Test note"},
            "message": "Note saved"
        }
        
        agent = NoteAgent(mcp_client=mock_mcp)
        result = await agent.handle({"text": "Test note", "title": "Test"})
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once_with("notes", "write", {
            "text": "Test note",
            "title": "Test"
        })
    
    @pytest.mark.asyncio
    async def test_note_agent_write_with_content_param(self, mock_mcp):
        """Test NoteAgent with 'content' parameter"""
        mock_mcp.call.return_value = {"status": "ok", "result": {}, "message": ""}
        
        agent = NoteAgent(mcp_client=mock_mcp)
        result = await agent.handle({"content": "Note content"})
        
        assert result["status"] == "ok"
        call_args = mock_mcp.call.call_args
        assert call_args[0][2]["text"] == "Note content"
    
    @pytest.mark.asyncio
    async def test_note_agent_list_notes(self, mock_mcp):
        """Test NoteAgent listing notes"""
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": [{"id": 1, "text": "Note 1"}],
            "message": "Found 1 notes"
        }
        
        agent = NoteAgent(mcp_client=mock_mcp)
        result = await agent.handle({"action": "list_notes"})
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once_with("notes", "list", {})
    
    @pytest.mark.asyncio
    async def test_note_agent_without_text(self, mock_mcp):
        """Test NoteAgent without text parameter"""
        agent = NoteAgent(mcp_client=mock_mcp)
        result = await agent.handle({})
        
        assert result["status"] == "error"
        assert "text is required" in result["message"]
    
    @pytest.mark.asyncio
    async def test_note_agent_without_mcp(self):
        """Test NoteAgent without MCP client"""
        agent = NoteAgent()
        result = await agent.handle({"text": "Test"})
        
        assert result["status"] == "error"
        assert "MCP client not available" in result["message"]



class TestCalendarAgent:
    """Test cases for CalendarAgent"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_calendar_agent_add_event(self, mock_mcp):
        """Test CalendarAgent adding an event"""
        from agents.calendar_agent import CalendarAgent
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {"id": 1, "title": "Meeting"},
            "message": "Event added"
        }
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        result = await agent.handle({
            "action": "calendar_add",
            "title": "Meeting",
            "date": "2024-01-01",
            "time": "09:00"
        })
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calendar_agent_list_events(self, mock_mcp):
        """Test CalendarAgent listing events"""
        from agents.calendar_agent import CalendarAgent
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": [{"id": 1, "title": "Event 1"}],
            "message": "Found 1 events"
        }
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        result = await agent.handle({"action": "list"})
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once_with("calendar_mock", "list_events", {
            "range_start": None,
            "range_end": None
        })
    
    @pytest.mark.asyncio
    async def test_calendar_agent_without_title(self, mock_mcp):
        """Test CalendarAgent without event title"""
        from agents.calendar_agent import CalendarAgent
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        result = await agent.handle({"action": "add"})
        
        assert result["status"] == "error"
        assert "title is required" in result["message"]


class TestWebAgent:
    """Test cases for WebAgent"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.mark.asyncio
    async def test_web_agent_fetch_url(self, mock_mcp):
        """Test WebAgent fetching a URL"""
        from agents.web_agent import WebAgent
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {"text": "content", "status_code": 200},
            "message": "Fetched"
        }
        
        agent = WebAgent(mcp_client=mock_mcp)
        result = await agent.handle({"url": "https://example.com"})
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_web_agent_search_query(self, mock_mcp):
        """Test WebAgent with search query"""
        from agents.web_agent import WebAgent
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {"text": "search results"},
            "message": "Fetched"
        }
        
        agent = WebAgent(mcp_client=mock_mcp)
        result = await agent.handle({"query": "python news"})
        
        assert result["status"] == "ok"
        # Should convert query to URL
        call_args = mock_mcp.call.call_args
        assert "url" in call_args[0][2]
    
    @pytest.mark.asyncio
    async def test_web_agent_without_url_or_query(self, mock_mcp):
        """Test WebAgent without URL or query"""
        from agents.web_agent import WebAgent
        
        agent = WebAgent(mcp_client=mock_mcp)
        result = await agent.handle({})
        
        assert result["status"] == "error"
        assert "URL or query is required" in result["message"]


class TestFallbackAgent:
    """Test cases for FallbackAgent"""
    
    @pytest.mark.asyncio
    async def test_fallback_agent_handles_unknown(self):
        """Test FallbackAgent handling unknown request"""
        from agents.fallback_agent import FallbackAgent
        
        agent = FallbackAgent()
        result = await agent.handle({"unknown": "param"})
        
        assert result["status"] == "ok"
        assert "잘 모르겠어요" in result["message"]
        assert "params" in result["result"]
    
    @pytest.mark.asyncio
    async def test_fallback_agent_includes_debug_info(self):
        """Test FallbackAgent includes debug information"""
        from agents.fallback_agent import FallbackAgent
        
        agent = FallbackAgent()
        params = {"test": "value"}
        result = await agent.handle(params)
        
        assert result["result"]["params"] == params
        assert result["result"]["agent"] == "FallbackAgent"
