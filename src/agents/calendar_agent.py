"""
CalendarAgent - Handles calendar operations using Notion
"""
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase


class CalendarAgent(AgentBase):
    """Agent for calendar operations using Notion Calendar"""
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle calendar operation requests
        
        Supported operations:
        - calendar_list: List calendar events
        - calendar_add: Add a new event
        
        Args:
            params: Dictionary with event details or date range
            
        Returns:
            Dictionary with status, result, and message
        """
        if self.mcp is None:
            return self._create_error_response("MCP client not available")
        
        # Determine action
        action = params.get("action", "list")
        
        try:
            if action in ["calendar_add", "add"]:
                # Add event
                title = params.get("title", "")
                date = params.get("date", "")
                time = params.get("time", "")
                description = params.get("description", "")
                
                if not title:
                    return self._create_error_response("Event title is required")
                
                result = await self.mcp.call("notion_calendar", "add_event", {
                    "title": title,
                    "date": date,
                    "time": time,
                    "description": description
                })
            else:
                # List events (default)
                range_start = params.get("range_start") or params.get("start_date")
                range_end = params.get("range_end") or params.get("end_date")
                
                result = await self.mcp.call("notion_calendar", "list_events", {
                    "range_start": range_start,
                    "range_end": range_end
                })
            
            return result
            
        except Exception as e:
            return self._create_error_response(
                message=f"Error handling calendar operation",
                error=e
            )
