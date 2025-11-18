"""
WebAgent - Handles web requests and search
"""
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase


class WebAgent(AgentBase):
    """Agent for web requests and search"""
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle web operation requests
        
        Supported operations:
        - web_search: Fetch content from URL or search query
        - fetch: Direct HTTP request
        
        Args:
            params: Dictionary with 'url' or 'query'
            
        Returns:
            Dictionary with status, result, and message
        """
        if self.mcp is None:
            return self._create_error_response("MCP client not available")
        
        # Get URL or query
        url = params.get("url")
        query = params.get("query")
        
        if not url and not query:
            return self._create_error_response("URL or query is required")
        
        # If query is provided, convert to search URL (simplified)
        if query and not url:
            # For demo purposes, just use a placeholder
            # In real implementation, this would use a search API
            url = f"https://www.google.com/search?q={query}"
        
        try:
            # Fetch URL
            result = await self.mcp.call("http_fetcher", "fetch", {"url": url})
            
            return result
            
        except Exception as e:
            return self._create_error_response(
                message=f"Error handling web request",
                error=e
            )
