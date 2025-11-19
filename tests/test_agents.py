import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base import AgentBase
from agents.note_agent import NoteAgent


# Concrete implementation for testing
class ConcreteTestAgent(AgentBase):
    """Concrete test agent implementation"""
    
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
        agent = ConcreteTestAgent()
        assert agent.mcp is None
        assert agent.llm is None
    
    def test_agent_initialization_with_clients(self):
        """Test agent initialization with clients"""
        mock_mcp = "mock_mcp_client"
        mock_llm = "mock_llm_client"
        
        agent = ConcreteTestAgent(mcp_client=mock_mcp, llm_client=mock_llm)
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
        agent = ConcreteTestAgent()
        result = await agent.handle({})
        
        assert isinstance(result, dict)
        assert "status" in result
        assert "result" in result
    
    def test_create_success_response(self):
        """Test creating success response"""
        agent = ConcreteTestAgent()
        response = agent._create_success_response(
            result={"data": "test"},
            message="Success"
        )
        
        assert response["status"] == "ok"
        assert response["result"] == {"data": "test"}
        assert response["message"] == "Success"
    
    def test_create_success_response_without_message(self):
        """Test creating success response without message"""
        agent = ConcreteTestAgent()
        response = agent._create_success_response(result="test_data")
        
        assert response["status"] == "ok"
        assert response["result"] == "test_data"
        assert response["message"] == ""
    
    def test_create_error_response(self):
        """Test creating error response"""
        agent = ConcreteTestAgent()
        response = agent._create_error_response(message="Test error")
        
        assert response["status"] == "error"
        assert response["result"] is None
        assert response["message"] == "Test error"
    
    def test_create_error_response_with_exception(self):
        """Test creating error response with exception"""
        agent = ConcreteTestAgent()
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
        agent = ConcreteTestAgent()
        assert agent.get_agent_name() == "ConcreteTestAgent"
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_without_client(self):
        """Test respond_via_llm without LLM client"""
        agent = ConcreteTestAgent()
        response = await agent.respond_via_llm("test prompt")
        
        assert response == "LLM client not available"
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_with_client(self):
        """Test respond_via_llm with LLM client"""
        agent = ConcreteTestAgent(llm_client="mock_llm")
        response = await agent.respond_via_llm("test prompt")
        
        # Should return placeholder for now
        assert "Response for:" in response
    
    @pytest.mark.asyncio
    async def test_respond_via_llm_with_context(self):
        """Test respond_via_llm with context"""
        agent = ConcreteTestAgent(llm_client="mock_llm")
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



class TestNoteAgent:
    """Test cases for NoteAgent"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI 생성 제목"
        return mock_response
    
    @pytest.mark.asyncio
    async def test_note_agent_write_note_with_ai_title(self, mock_mcp, mock_openai_response):
        """Test NoteAgent writing a note with AI-generated title"""
        from unittest.mock import patch
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {
                "id": "page-123",
                "title": "AI 생성 제목",
                "content": "Test note content",
                "created_at": "2024-01-15T10:30:00.000Z",
                "url": "https://notion.so/page-123"
            },
            "message": "Note created in Notion"
        }
        
        agent = NoteAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response
            
            result = await agent.handle({"text": "Test note content"})
            
            assert result["status"] == "ok"
            assert result["result"]["id"] == "page-123"
            
            # Verify AI title generation was called
            mock_create.assert_called_once()
            
            # Verify MCP was called with AI-generated title
            call_args = mock_mcp.call.call_args
            assert call_args[0][0] == "notion_notes"
            assert call_args[0][1] == "write"
            assert call_args[0][2]["text"] == "Test note content"
            assert call_args[0][2]["title"] == "AI 생성 제목"
    
    @pytest.mark.asyncio
    async def test_note_agent_write_with_content_param(self, mock_mcp, mock_openai_response):
        """Test NoteAgent with 'content' parameter"""
        from unittest.mock import patch
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {
                "id": "page-456",
                "title": "AI 생성 제목",
                "content": "Note content",
                "created_at": "2024-01-15T10:30:00.000Z",
                "url": "https://notion.so/page-456"
            },
            "message": "Note created"
        }
        
        agent = NoteAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response
            
            result = await agent.handle({"content": "Note content"})
            
            assert result["status"] == "ok"
            call_args = mock_mcp.call.call_args
            assert call_args[0][0] == "notion_notes"
            assert call_args[0][2]["text"] == "Note content"
            assert call_args[0][2]["title"] == "AI 생성 제목"
    
    @pytest.mark.asyncio
    async def test_note_agent_title_generation_fallback(self, mock_mcp):
        """Test NoteAgent falls back to first line when AI fails"""
        from unittest.mock import patch
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {
                "id": "page-789",
                "title": "First line of content",
                "content": "First line of content\nMore content here",
                "created_at": "2024-01-15T10:30:00.000Z",
                "url": "https://notion.so/page-789"
            },
            "message": "Note created"
        }
        
        agent = NoteAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = await agent.handle({"text": "First line of content\nMore content here"})
            
            assert result["status"] == "ok"
            # Should use first line as fallback
            call_args = mock_mcp.call.call_args
            assert "First line of content" in call_args[0][2]["title"]
    
    @pytest.mark.asyncio
    async def test_note_agent_list_notes(self, mock_mcp):
        """Test NoteAgent listing notes from Notion"""
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": [
                {
                    "id": "page-1",
                    "title": "Note 1",
                    "content": "Content 1",
                    "created_at": "2024-01-15T10:30:00.000Z",
                    "url": "https://notion.so/page-1"
                }
            ],
            "message": "Found 1 notes"
        }
        
        agent = NoteAgent(mcp_client=mock_mcp)
        result = await agent.handle({"action": "list_notes"})
        
        assert result["status"] == "ok"
        assert len(result["result"]) == 1
        assert result["result"][0]["id"] == "page-1"
        mock_mcp.call.assert_called_once_with("notion_notes", "list", {})
    
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
    
    @pytest.mark.asyncio
    async def test_note_agent_list_with_action_list(self, mock_mcp):
        """Test NoteAgent listing with 'list' action"""
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": [],
            "message": "No notes found"
        }
        
        agent = NoteAgent(mcp_client=mock_mcp)
        result = await agent.handle({"action": "list"})
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once_with("notion_notes", "list", {})



class TestCalendarAgent:
    """Test cases for CalendarAgent"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI response"""
        def _create_response(content: str):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = content
            return mock_response
        return _create_response
    
    @pytest.mark.asyncio
    async def test_calendar_agent_add_event_with_structured_data(self, mock_mcp):
        """Test CalendarAgent adding an event with structured data"""
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
    async def test_calendar_agent_add_event_with_llm_extraction(self, mock_mcp, mock_openai_response):
        """Test CalendarAgent extracting event data from text using LLM"""
        from agents.calendar_agent import CalendarAgent
        from unittest.mock import patch
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {"id": 1, "title": "팀 회의"},
            "message": "Event added"
        }
        
        llm_response = '{"title": "팀 회의", "date": "2024-01-15", "time": "15:00", "description": ""}'
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(llm_response)
            
            result = await agent.handle({
                "action": "calendar_add",
                "text": "오늘 오후 3시에 팀 회의"
            })
            
            assert result["status"] == "ok"
            mock_create.assert_called_once()
            
            # Verify MCP was called with extracted data
            call_args = mock_mcp.call.call_args
            assert call_args[0][0] == "notion_calendar"
            assert call_args[0][1] == "add_event"
            assert call_args[0][2]["title"] == "팀 회의"
    
    @pytest.mark.asyncio
    async def test_calendar_agent_list_events_with_structured_data(self, mock_mcp):
        """Test CalendarAgent listing events with structured data"""
        from agents.calendar_agent import CalendarAgent
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": [{"id": 1, "title": "Event 1"}],
            "message": "Found 1 events"
        }
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        result = await agent.handle({
            "action": "list",
            "range_start": "2024-01-01",
            "range_end": "2024-01-31"
        })
        
        assert result["status"] == "ok"
        mock_mcp.call.assert_called_once_with("notion_calendar", "list_events", {
            "range_start": "2024-01-01",
            "range_end": "2024-01-31"
        })
    
    @pytest.mark.asyncio
    async def test_calendar_agent_list_events_with_llm_extraction(self, mock_mcp, mock_openai_response):
        """Test CalendarAgent extracting date range from text using LLM"""
        from agents.calendar_agent import CalendarAgent
        from unittest.mock import patch
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": [{"id": 1, "title": "Event 1"}],
            "message": "Found 1 events"
        }
        
        llm_response = '{"range_start": "2024-01-15", "range_end": "2024-01-21"}'
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(llm_response)
            
            result = await agent.handle({
                "action": "list",
                "text": "이번주 일정 알려줘"
            })
            
            assert result["status"] == "ok"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calendar_agent_without_event_info(self, mock_mcp):
        """Test CalendarAgent without event information"""
        from agents.calendar_agent import CalendarAgent
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        result = await agent.handle({"action": "add"})
        
        assert result["status"] == "error"
        assert "required" in result["message"]
    
    @pytest.mark.asyncio
    async def test_calendar_agent_llm_extraction_fallback(self, mock_mcp, mock_openai_response):
        """Test CalendarAgent fallback when LLM extraction fails"""
        from agents.calendar_agent import CalendarAgent
        from unittest.mock import patch
        
        mock_mcp.call.return_value = {
            "status": "ok",
            "result": {"id": 1, "title": "회의"},
            "message": "Event added"
        }
        
        agent = CalendarAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = await agent.handle({
                "action": "calendar_add",
                "text": "회의"
            })
            
            assert result["status"] == "ok"
            # Should use fallback (text as title)
            call_args = mock_mcp.call.call_args
            assert call_args[0][2]["title"] == "회의"


class TestWebAgent:
    """Test cases for WebAgent"""
    
    @pytest.fixture
    def mock_mcp(self):
        """Create mock MCP client"""
        mock = MagicMock()
        mock.call = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "요약된 검색 결과입니다."
        return mock_response
    
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
    async def test_web_agent_search_with_summarization(self, mock_mcp, mock_openai_response):
        """Test WebAgent searching and summarizing top 3 results"""
        from agents.web_agent import WebAgent
        from unittest.mock import patch
        
        # Mock search results
        search_results = [
            {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
            {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"},
            {"title": "Result 3", "url": "https://example.com/3", "snippet": "Snippet 3"}
        ]
        
        # Mock fetch_and_extract results
        fetch_results = [
            {"status": "ok", "result": {"url": "https://example.com/1", "text": "Content 1"}},
            {"status": "ok", "result": {"url": "https://example.com/2", "text": "Content 2"}},
            {"status": "ok", "result": {"url": "https://example.com/3", "text": "Content 3"}}
        ]
        
        async def mock_call_side_effect(tool, action, params):
            if action == "search":
                return {"status": "ok", "result": search_results, "message": "Found 3 results"}
            elif action == "fetch_and_extract":
                url = params["url"]
                for i, result in enumerate(search_results):
                    if result["url"] == url:
                        return fetch_results[i]
            return {"status": "error", "result": None, "message": "Unknown action"}
        
        mock_mcp.call.side_effect = mock_call_side_effect
        
        agent = WebAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response
            
            result = await agent.handle({"query": "Python programming"})
            
            assert result["status"] == "ok"
            assert "summary" in result["result"]
            assert "sources" in result["result"]
            assert len(result["result"]["sources"]) == 3
            assert result["result"]["query"] == "Python programming"
            
            # Verify LLM was called for summarization
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_web_agent_search_no_results(self, mock_mcp):
        """Test WebAgent when search returns no results"""
        from agents.web_agent import WebAgent
        
        mock_mcp.call.return_value = {
            "status": "error",
            "result": None,
            "message": "No search results found"
        }
        
        agent = WebAgent(mcp_client=mock_mcp)
        result = await agent.handle({"query": "nonexistent query"})
        
        assert result["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_web_agent_search_fetch_failure(self, mock_mcp, mock_openai_response):
        """Test WebAgent when fetching content fails for all results"""
        from agents.web_agent import WebAgent
        from unittest.mock import patch
        
        search_results = [
            {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"}
        ]
        
        async def mock_call_side_effect(tool, action, params):
            if action == "search":
                return {"status": "ok", "result": search_results, "message": "Found 1 result"}
            elif action == "fetch_and_extract":
                return {"status": "error", "result": None, "message": "Fetch failed"}
            return {"status": "error", "result": None, "message": "Unknown action"}
        
        mock_mcp.call.side_effect = mock_call_side_effect
        
        agent = WebAgent(mcp_client=mock_mcp)
        result = await agent.handle({"query": "test query"})
        
        assert result["status"] == "error"
        assert "가져올 수 없습니다" in result["message"]
    
    @pytest.mark.asyncio
    async def test_web_agent_search_partial_fetch_success(self, mock_mcp, mock_openai_response):
        """Test WebAgent when some fetches succeed and some fail"""
        from agents.web_agent import WebAgent
        from unittest.mock import patch
        
        search_results = [
            {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1"},
            {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2"}
        ]
        
        async def mock_call_side_effect(tool, action, params):
            if action == "search":
                return {"status": "ok", "result": search_results, "message": "Found 2 results"}
            elif action == "fetch_and_extract":
                if params["url"] == "https://example.com/1":
                    return {"status": "ok", "result": {"url": params["url"], "text": "Content 1"}}
                else:
                    return {"status": "error", "result": None, "message": "Fetch failed"}
            return {"status": "error", "result": None, "message": "Unknown action"}
        
        mock_mcp.call.side_effect = mock_call_side_effect
        
        agent = WebAgent(mcp_client=mock_mcp)
        
        with patch.object(agent.openai_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response
            
            result = await agent.handle({"query": "test query"})
            
            assert result["status"] == "ok"
            assert len(result["result"]["sources"]) == 1  # Only successful fetch
    
    @pytest.mark.asyncio
    async def test_web_agent_without_url_or_query(self, mock_mcp):
        """Test WebAgent without URL or query"""
        from agents.web_agent import WebAgent
        
        agent = WebAgent(mcp_client=mock_mcp)
        result = await agent.handle({})
        
        assert result["status"] == "error"
        assert "URL or query is required" in result["message"]
    
    @pytest.mark.asyncio
    async def test_web_agent_without_mcp(self):
        """Test WebAgent without MCP client"""
        from agents.web_agent import WebAgent
        
        agent = WebAgent()
        result = await agent.handle({"query": "test"})
        
        assert result["status"] == "error"
        assert "MCP client not available" in result["message"]


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
