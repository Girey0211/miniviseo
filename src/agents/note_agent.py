"""
NoteAgent - Handles note management
"""
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase


class NoteAgent(AgentBase):
    """Agent for note management operations"""
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle note operation requests
        
        Supported operations:
        - write_note: Create a new note
        - list_notes: List all notes
        
        Args:
            params: Dictionary with 'text', 'content', 'title', or 'action'
            
        Returns:
            Dictionary with status, result, and message
        """
        if self.mcp is None:
            return self._create_error_response("MCP client not available")
        
        # Determine action
        action = params.get("action", "write_note")
        
        try:
            if action == "list_notes" or action == "list":
                # List notes
                result = await self.mcp.call("notes", "list", {})
            else:
                # Write note (default)
                text = params.get("text") or params.get("content", "")
                title = params.get("title", "")
                
                if not text:
                    return self._create_error_response("Note text is required")
                
                result = await self.mcp.call("notes", "write", {
                    "text": text,
                    "title": title
                })
            
            return result
            
        except Exception as e:
            return self._create_error_response(
                message=f"Error handling note operation",
                error=e
            )
