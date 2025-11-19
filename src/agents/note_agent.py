"""
NoteAgent - Handles note management
"""
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL


class NoteAgent(AgentBase):
    """Agent for note management operations"""
    
    def __init__(self, mcp_client=None, llm_client=None):
        super().__init__(mcp_client, llm_client)
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
    
    async def _generate_title(self, content: str) -> str:
        """
        Generate a concise title from note content using AI
        
        Args:
            content: Note content text
            
        Returns:
            Generated title (max 50 characters)
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates concise titles. Generate a short, descriptive title (max 50 characters) in Korean for the given note content. Return ONLY the title, no quotes or extra text."
                    },
                    {
                        "role": "user",
                        "content": f"Create a title for this note:\n\n{content[:500]}"
                    }
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            title = response.choices[0].message.content.strip()
            # Remove quotes if present
            title = title.strip('"').strip("'")
            # Limit to 50 characters
            return title[:50]
            
        except Exception as e:
            # Fallback to first line if AI generation fails
            return content.split('\n')[0][:50]
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle note operation requests using Notion API
        
        Supported operations:
        - write_note: Create a new note in Notion
        - list_notes: List all notes from Notion
        
        Args:
            params: Dictionary with 'text', 'content', 'title', 'action', or 'previous_results'
            
        Returns:
            Dictionary with status, result, and message
        """
        if self.mcp is None:
            return self._create_error_response("MCP client not available")
        
        # Determine action from intent or action parameter
        intent = params.get("intent", "")
        action = params.get("action", "write_note")
        
        try:
            if intent == "list_notes" or action == "list_notes" or action == "list":
                # List notes from Notion
                result = await self.mcp.call("notion_notes", "list", {})
            else:
                # Write note to Notion (default)
                text = params.get("text") or params.get("content", "")
                
                # Check if there are previous results to incorporate
                previous_results = params.get("previous_results", [])
                if previous_results and not text:
                    # Extract content from previous results (e.g., web search results)
                    for prev in previous_results:
                        prev_result = prev.get("result", {})
                        if prev_result.get("status") == "ok":
                            prev_data = prev_result.get("result", "")
                            
                            # Handle different result formats
                            if isinstance(prev_data, str):
                                text = prev_data
                                break
                            elif isinstance(prev_data, dict):
                                # For web search results with summary
                                if "summary" in prev_data:
                                    text = prev_data["summary"]
                                    # Optionally add sources
                                    if "sources" in prev_data:
                                        sources_text = "\n\n참고 링크:\n"
                                        for source in prev_data["sources"]:
                                            sources_text += f"- {source['title']}: {source['url']}\n"
                                        text += sources_text
                                    break
                                else:
                                    text = str(prev_data)
                                    break
                
                if not text:
                    return self._create_error_response("Note text is required")
                
                # Generate title from content using AI
                title = await self._generate_title(text)
                
                result = await self.mcp.call("notion_notes", "write", {
                    "text": text,
                    "title": title
                })
            
            return result
            
        except Exception as e:
            return self._create_error_response(
                message=f"Error handling note operation",
                error=e
            )
