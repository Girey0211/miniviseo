"""
FileAgent - Handles file operations
"""
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase


class FileAgent(AgentBase):
    """Agent for file system operations"""
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle file operation requests
        
        Supported operations:
        - list_files: List files in a directory
        - read_file: Read file contents
        
        Args:
            params: Dictionary with 'path' and optional 'action'
            
        Returns:
            Dictionary with status, result, and message
        """
        if self.mcp is None:
            return self._create_error_response("MCP client not available")
        
        # Determine action (can be inferred from params or explicit)
        action = params.get("action", "list_files")
        path = params.get("path", ".")
        
        try:
            # Route to appropriate MCP tool action
            if action == "read_file" or "file" in path.lower() and "." in path:
                # Read file
                result = await self.mcp.call("file_manager", "read_file", {"path": path})
            else:
                # List files (default)
                result = await self.mcp.call("file_manager", "list_files", {"path": path})
            
            return result
            
        except Exception as e:
            return self._create_error_response(
                message=f"Error handling file operation",
                error=e
            )
