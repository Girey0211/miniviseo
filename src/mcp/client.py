"""
MCP Client - Abstraction layer for MCP tool execution
"""
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))


class MCPClient:
    """
    MCP Client for executing tool actions
    
    This is a simple implementation that routes calls to tool modules.
    """
    
    def __init__(self):
        """Initialize MCP client with tool registry"""
        self.tools = {}
    
    def register_tool(self, tool_name: str, tool_module):
        """
        Register a tool module
        
        Args:
            tool_name: Name of the tool (e.g., "file_manager")
            tool_module: Tool module with action functions
        """
        self.tools[tool_name] = tool_module
    
    async def call(self, tool_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool action with parameters
        
        Args:
            tool_name: Name of the tool (e.g., "file_manager")
            action: Action to perform (e.g., "list_files")
            params: Parameters for the action
            
        Returns:
            Dictionary with status, result, and optional message
        """
        # Get tool module
        tool = self.tools.get(tool_name)
        
        if tool is None:
            return {
                "status": "error",
                "result": None,
                "message": f"Tool '{tool_name}' not found"
            }
        
        # Get action function
        action_fn = getattr(tool, action, None)
        
        if action_fn is None:
            return {
                "status": "error",
                "result": None,
                "message": f"Action '{action}' not found in tool '{tool_name}'"
            }
        
        # Execute action
        try:
            result = await action_fn(**params)
            return result
        except Exception as e:
            return {
                "status": "error",
                "result": None,
                "message": f"Error executing {tool_name}.{action}: {str(e)}"
            }


# Global MCP client instance
_mcp_client = MCPClient()


def get_mcp_client() -> MCPClient:
    """Get global MCP client instance"""
    return _mcp_client


def register_tool(tool_name: str, tool_module):
    """Convenience function to register a tool"""
    _mcp_client.register_tool(tool_name, tool_module)
