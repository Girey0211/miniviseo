import pytest
import sys
from pathlib import Path
from hypothesis import given, strategies as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from router.agent_router import AgentRouter, route_to_agent, register_agent, get_router, INTENT_MAP
from parser.schemas import ParsedRequest


# Mock agent classes for testing
class MockFileAgent:
    """Mock FileAgent"""
    pass


class MockNoteAgent:
    """Mock NoteAgent"""
    pass


class MockCalendarAgent:
    """Mock CalendarAgent"""
    pass


class MockWebAgent:
    """Mock WebAgent"""
    pass


class MockFallbackAgent:
    """Mock FallbackAgent"""
    pass


@pytest.fixture
def router():
    """Create a fresh router instance for each test"""
    router = AgentRouter()
    # Register mock agents
    router.register_agent("FileAgent", MockFileAgent)
    router.register_agent("NoteAgent", MockNoteAgent)
    router.register_agent("CalendarAgent", MockCalendarAgent)
    router.register_agent("WebAgent", MockWebAgent)
    router.register_agent("FallbackAgent", MockFallbackAgent)
    return router


class TestAgentRouter:
    """Test cases for AgentRouter"""
    
    def test_intent_map_completeness(self):
        """Test that all expected intents are mapped"""
        expected_intents = [
            "write_note", "list_notes",
            "calendar_list", "calendar_add", "web_search", "unknown"
        ]
        
        for intent in expected_intents:
            assert intent in INTENT_MAP
    
    def test_file_intents_not_in_map(self):
        """Test that file-related intents are not in INTENT_MAP"""
        file_intents = ["list_files", "read_file"]
        
        for intent in file_intents:
            assert intent not in INTENT_MAP, \
                f"File intent '{intent}' should not be in INTENT_MAP"
    
    def test_register_agent(self, router):
        """Test agent registration"""
        class TestAgent:
            pass
        
        router.register_agent("TestAgent", TestAgent)
        assert "TestAgent" in router._agent_registry
        assert router._agent_registry["TestAgent"] == TestAgent
    
    def test_get_agent_name_from_parsed_agent_field(self, router):
        """Test getting agent name from parsed.agent field"""
        parsed = ParsedRequest(
            intent="list_files",
            agent="FileAgent",
            params={"path": "downloads"}
        )
        
        agent_name = router.get_agent_name(parsed)
        assert agent_name == "FileAgent"
    
    def test_get_agent_name_from_intent_mapping(self, router):
        """Test getting agent name from intent mapping"""
        parsed = ParsedRequest(
            intent="write_note",
            agent="UnknownAgent",  # Not registered
            params={}
        )
        
        agent_name = router.get_agent_name(parsed)
        assert agent_name == "NoteAgent"  # Should fall back to intent mapping
    
    def test_route_list_files_to_fallback_agent(self, router):
        """Test routing list_files intent to FallbackAgent (file intents removed)"""
        parsed = ParsedRequest(
            intent="list_files",
            agent="UnknownAgent",
            params={"path": "downloads"}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockFallbackAgent
    
    def test_route_read_file_to_fallback_agent(self, router):
        """Test routing read_file intent to FallbackAgent (file intents removed)"""
        parsed = ParsedRequest(
            intent="read_file",
            agent="UnknownAgent",
            params={"path": "test.txt"}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockFallbackAgent
    
    def test_route_write_note_to_note_agent(self, router):
        """Test routing write_note intent to NoteAgent"""
        parsed = ParsedRequest(
            intent="write_note",
            agent="NoteAgent",
            params={"text": "test note"}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockNoteAgent
    
    def test_route_list_notes_to_note_agent(self, router):
        """Test routing list_notes intent to NoteAgent"""
        parsed = ParsedRequest(
            intent="list_notes",
            agent="NoteAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockNoteAgent
    
    def test_route_calendar_list_to_calendar_agent(self, router):
        """Test routing calendar_list intent to CalendarAgent"""
        parsed = ParsedRequest(
            intent="calendar_list",
            agent="CalendarAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockCalendarAgent
    
    def test_route_calendar_add_to_calendar_agent(self, router):
        """Test routing calendar_add intent to CalendarAgent"""
        parsed = ParsedRequest(
            intent="calendar_add",
            agent="CalendarAgent",
            params={"title": "meeting", "time": "09:00"}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockCalendarAgent
    
    def test_route_web_search_to_web_agent(self, router):
        """Test routing web_search intent to WebAgent"""
        parsed = ParsedRequest(
            intent="web_search",
            agent="WebAgent",
            params={"query": "python news"}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockWebAgent
    
    def test_route_unknown_to_fallback_agent(self, router):
        """Test routing unknown intent to FallbackAgent"""
        parsed = ParsedRequest(
            intent="unknown",
            agent="FallbackAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockFallbackAgent
    
    def test_route_unregistered_agent_to_fallback(self, router):
        """Test routing to FallbackAgent when agent not registered"""
        parsed = ParsedRequest(
            intent="unknown_intent",
            agent="NonExistentAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(parsed)
        assert agent_class == MockFallbackAgent
    
    def test_get_agent_for_intent(self, router):
        """Test getting agent name for specific intent"""
        assert router.get_agent_for_intent("write_note") == "NoteAgent"
        assert router.get_agent_for_intent("calendar_add") == "CalendarAgent"
        assert router.get_agent_for_intent("web_search") == "WebAgent"
        assert router.get_agent_for_intent("unknown") == "FallbackAgent"
    
    def test_get_agent_for_file_intents_returns_none(self, router):
        """Test that file intents return None (not in INTENT_MAP)"""
        assert router.get_agent_for_intent("list_files") is None
        assert router.get_agent_for_intent("read_file") is None
    
    def test_get_agent_for_invalid_intent(self, router):
        """Test getting agent for invalid intent returns None"""
        assert router.get_agent_for_intent("invalid_intent") is None


class TestRouterConvenienceFunctions:
    """Test convenience functions"""
    
    def test_get_router(self):
        """Test getting global router instance"""
        router = get_router()
        assert isinstance(router, AgentRouter)
    
    def test_register_agent_convenience(self):
        """Test convenience function for registering agent"""
        class TestAgent:
            pass
        
        register_agent("TestAgent", TestAgent)
        router = get_router()
        assert "TestAgent" in router._agent_registry
    
    def test_route_to_agent_convenience(self):
        """Test convenience function for routing"""
        # Register a test agent
        register_agent("FallbackAgent", MockFallbackAgent)
        
        parsed = ParsedRequest(
            intent="unknown",
            agent="FallbackAgent",
            params={}
        )
        
        agent_class = route_to_agent(parsed)
        assert agent_class == MockFallbackAgent


class TestIntentMapping:
    """Test intent to agent mapping"""
    
    def test_file_intents_not_in_map(self):
        """Test file-related intents are not in INTENT_MAP"""
        assert "list_files" not in INTENT_MAP
        assert "read_file" not in INTENT_MAP
    
    def test_note_intents_map_to_note_agent(self):
        """Test note-related intents map to NoteAgent"""
        assert INTENT_MAP["write_note"] == "NoteAgent"
        assert INTENT_MAP["list_notes"] == "NoteAgent"
    
    def test_calendar_intents_map_to_calendar_agent(self):
        """Test calendar-related intents map to CalendarAgent"""
        assert INTENT_MAP["calendar_list"] == "CalendarAgent"
        assert INTENT_MAP["calendar_add"] == "CalendarAgent"
    
    def test_web_intents_map_to_web_agent(self):
        """Test web-related intents map to WebAgent"""
        assert INTENT_MAP["web_search"] == "WebAgent"
    
    def test_unknown_intent_maps_to_fallback_agent(self):
        """Test unknown intent maps to FallbackAgent"""
        assert INTENT_MAP["unknown"] == "FallbackAgent"



class TestPropertyBasedRouting:
    """Property-based tests for routing behavior"""
    
    @given(
        intent=st.sampled_from(["list_files", "read_file"]),
        agent=st.text(min_size=1, max_size=20),
        params=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=5
        )
    )
    def test_file_intent_fallback_routing(self, intent, agent, params):
        """
        **Feature: agent-refactoring, Property 1: File intent fallback routing**
        
        Property: For any user request with file-related intent (list_files, read_file),
        the system should route to FallbackAgent
        
        **Validates: Requirements 1.2**
        """
        # Setup router with FallbackAgent registered
        router = AgentRouter()
        router.register_agent("FallbackAgent", MockFallbackAgent)
        
        # Create parsed request with file-related intent
        parsed = ParsedRequest(
            intent=intent,
            agent=agent,
            params=params
        )
        
        # Route the request
        agent_class = router.route_to_agent(parsed)
        
        # Verify it routes to FallbackAgent
        assert agent_class == MockFallbackAgent, \
            f"File intent '{intent}' should route to FallbackAgent, but got {agent_class}"
