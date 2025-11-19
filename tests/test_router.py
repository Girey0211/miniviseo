import pytest
import sys
from pathlib import Path
from hypothesis import given, strategies as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from router.agent_router import AgentRouter, route_to_agent, register_agent, get_router, INTENT_MAP
from parser.schemas import AgentAction


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
    
    def test_get_agent_name_from_action_agent_field(self, router):
        """Test getting agent name from action.agent field"""
        action = AgentAction(
            intent="write_note",
            agent="NoteAgent",
            params={"text": "test"}
        )
        
        agent_name = router.get_agent_name(action)
        assert agent_name == "NoteAgent"
    
    def test_get_agent_name_from_intent_mapping(self, router):
        """Test getting agent name from intent mapping"""
        action = AgentAction(
            intent="write_note",
            agent="UnknownAgent",  # Not registered
            params={}
        )
        
        agent_name = router.get_agent_name(action)
        assert agent_name == "NoteAgent"  # Should fall back to intent mapping
    
    def test_route_write_note_to_note_agent(self, router):
        """Test routing write_note intent to NoteAgent"""
        action = AgentAction(
            intent="write_note",
            agent="NoteAgent",
            params={"text": "test note"}
        )
        
        agent_class = router.route_to_agent(action)
        assert agent_class == MockNoteAgent
    
    def test_route_list_notes_to_note_agent(self, router):
        """Test routing list_notes intent to NoteAgent"""
        action = AgentAction(
            intent="list_notes",
            agent="NoteAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(action)
        assert agent_class == MockNoteAgent
    
    def test_route_calendar_list_to_calendar_agent(self, router):
        """Test routing calendar_list intent to CalendarAgent"""
        action = AgentAction(
            intent="calendar_list",
            agent="CalendarAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(action)
        assert agent_class == MockCalendarAgent
    
    def test_route_calendar_add_to_calendar_agent(self, router):
        """Test routing calendar_add intent to CalendarAgent"""
        action = AgentAction(
            intent="calendar_add",
            agent="CalendarAgent",
            params={"title": "meeting", "time": "09:00"}
        )
        
        agent_class = router.route_to_agent(action)
        assert agent_class == MockCalendarAgent
    
    def test_route_web_search_to_web_agent(self, router):
        """Test routing web_search intent to WebAgent"""
        action = AgentAction(
            intent="web_search",
            agent="WebAgent",
            params={"query": "python news"}
        )
        
        agent_class = router.route_to_agent(action)
        assert agent_class == MockWebAgent
    
    def test_route_unknown_to_fallback_agent(self, router):
        """Test routing unknown intent to FallbackAgent"""
        action = AgentAction(
            intent="unknown",
            agent="FallbackAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(action)
        assert agent_class == MockFallbackAgent
    
    def test_route_unregistered_agent_to_fallback(self, router):
        """Test routing to FallbackAgent when agent not registered"""
        action = AgentAction(
            intent="unknown_intent",
            agent="NonExistentAgent",
            params={}
        )
        
        agent_class = router.route_to_agent(action)
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
        
        action = AgentAction(
            intent="unknown",
            agent="FallbackAgent",
            params={}
        )
        
        agent_class = route_to_agent(action)
        assert agent_class == MockFallbackAgent


class TestIntentMapping:
    """Test intent to agent mapping"""
    
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
        intent=st.sampled_from(["write_note", "list_notes", "calendar_add", "calendar_list", "web_search", "unknown"]),
        params=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=0, max_size=100),
            min_size=0,
            max_size=5
        )
    )
    def test_intent_routing_consistency(self, intent, params):
        """
        **Feature: multi-action-support, Property 1: Intent routing consistency**
        
        Property: For any valid intent with unregistered agent, the router should consistently route based on intent
        
        **Validates: Requirements 1.1**
        """
        # Setup router with all agents registered
        router = AgentRouter()
        router.register_agent("NoteAgent", MockNoteAgent)
        router.register_agent("CalendarAgent", MockCalendarAgent)
        router.register_agent("WebAgent", MockWebAgent)
        router.register_agent("FallbackAgent", MockFallbackAgent)
        
        # Create action with unregistered agent name to test intent-based routing
        action = AgentAction(
            intent=intent,
            agent="UnregisteredAgent",  # Use unregistered agent to force intent-based routing
            params=params
        )
        
        # Route the request
        agent_class = router.route_to_agent(action)
        
        # Verify it routes to correct agent based on intent
        expected_agent = INTENT_MAP.get(intent, "FallbackAgent")
        expected_class = {
            "NoteAgent": MockNoteAgent,
            "CalendarAgent": MockCalendarAgent,
            "WebAgent": MockWebAgent,
            "FallbackAgent": MockFallbackAgent
        }.get(expected_agent)
        
        assert agent_class == expected_class, \
            f"Intent '{intent}' should route to {expected_agent}, but got {agent_class}"
