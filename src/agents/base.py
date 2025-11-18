"""
AgentBase - Abstract base class for all agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class AgentBase(ABC):
    """
    Abstract base class for all agents
    
    All agents must inherit from this class and implement the handle method.
    """
    
    def __init__(self, mcp_client=None, llm_client=None):
        """
        Initialize agent
        
        Args:
            mcp_client: MCP client for tool execution
            llm_client: LLM client for response generation
        """
        self.mcp = mcp_client
        self.llm = llm_client
    
    @abstractmethod
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the request with given parameters
        
        Args:
            params: Dictionary of parameters from parsed request
            
        Returns:
            Dictionary with status, result, and optional message
            Format: {"status": "ok|error", "result": Any, "message": str}
        """
        raise NotImplementedError("Subclasses must implement handle method")
    
    async def respond_via_llm(self, prompt: str, context: Optional[Dict] = None) -> str:
        """
        Generate natural language response using LLM
        
        Args:
            prompt: Prompt for LLM
            context: Optional context dictionary
            
        Returns:
            Generated response string
        """
        if self.llm is None:
            return "LLM client not available"
        
        try:
            # This will be implemented when we integrate LLM for response generation
            # For now, return a placeholder
            return f"Response for: {prompt}"
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def _create_success_response(self, result: Any, message: str = "") -> Dict[str, Any]:
        """
        Create a success response dictionary
        
        Args:
            result: Result data
            message: Optional success message
            
        Returns:
            Success response dictionary
        """
        return {
            "status": "ok",
            "result": result,
            "message": message
        }
    
    def _create_error_response(self, message: str, error: Optional[Exception] = None) -> Dict[str, Any]:
        """
        Create an error response dictionary
        
        Args:
            message: Error message
            error: Optional exception object
            
        Returns:
            Error response dictionary
        """
        response = {
            "status": "error",
            "result": None,
            "message": message
        }
        
        if error:
            response["error_detail"] = str(error)
        
        return response
    
    def get_agent_name(self) -> str:
        """
        Get the name of this agent
        
        Returns:
            Agent class name
        """
        return self.__class__.__name__
