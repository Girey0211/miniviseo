"""
Agent Router - Routes parsed requests to appropriate agents
"""
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.schemas import AgentAction


# Intent to Agent mapping
INTENT_MAP = {
    "write_note": "NoteAgent",
    "list_notes": "NoteAgent",
    "calendar_list": "CalendarAgent",
    "calendar_add": "CalendarAgent",
    "web_search": "WebAgent",
    "unknown": "FallbackAgent",
}


class AgentRouter:
    """Routes requests to appropriate agents"""
    
    def __init__(self):
        self.intent_map = INTENT_MAP
        self._agent_registry = {}
    
    def register_agent(self, agent_name: str, agent_class):
        """
        Register an agent class
        
        Args:
            agent_name: Name of the agent (e.g., "NoteAgent")
            agent_class: Agent class to register
        """
        self._agent_registry[agent_name] = agent_class
    
    def get_agent_name(self, action: AgentAction) -> str:
        """
        Get agent name from action
        
        Args:
            action: AgentAction object
            
        Returns:
            Agent name string
        """
        # First try to use the agent field from action
        if action.agent and action.agent in self._agent_registry:
            return action.agent
        
        # Fall back to intent mapping
        agent_name = self.intent_map.get(action.intent, "FallbackAgent")
        
        return agent_name
    
    def route_to_agent(self, action: AgentAction):
        """
        Route action to appropriate agent instance
        
        Args:
            action: AgentAction object
            
        Returns:
            Agent instance or None if not found
        """
        agent_name = self.get_agent_name(action)
        
        # Get agent class from registry
        agent_class = self._agent_registry.get(agent_name)
        
        if agent_class is None:
            # Try to get FallbackAgent as last resort
            agent_class = self._agent_registry.get("FallbackAgent")
        
        if agent_class is None:
            return None
        
        # Return agent instance (agents should be instantiated elsewhere)
        return agent_class
    
    def get_agent_for_intent(self, intent: str) -> Optional[str]:
        """
        Get agent name for a given intent
        
        Args:
            intent: Intent string
            
        Returns:
            Agent name or None
        """
        return self.intent_map.get(intent)


# Global router instance
_router = AgentRouter()


def get_router() -> AgentRouter:
    """Get global router instance"""
    return _router


def route_to_agent(action: AgentAction):
    """
    Convenience function to route action to agent
    
    Args:
        action: AgentAction object
        
    Returns:
        Agent class
    """
    return _router.route_to_agent(action)


def register_agent(agent_name: str, agent_class):
    """
    Convenience function to register an agent
    
    Args:
        agent_name: Name of the agent
        agent_class: Agent class
    """
    _router.register_agent(agent_name, agent_class)
