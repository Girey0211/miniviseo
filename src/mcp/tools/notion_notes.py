"""
Notion Notes MCP Tool - Notes integration with Notion
"""
import os
import asyncio
from datetime import datetime
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False


# Notion configuration
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_NOTES_DATABASE_ID = os.getenv("NOTION_NOTES_DATABASE_ID")


def _format_database_id(db_id: str) -> str:
    """Format database ID to UUID format with hyphens"""
    if not db_id:
        return db_id
    # Remove existing hyphens
    db_id = db_id.replace("-", "")
    # Add hyphens in UUID format
    if len(db_id) == 32:
        return f"{db_id[:8]}-{db_id[8:12]}-{db_id[12:16]}-{db_id[16:20]}-{db_id[20:]}"
    return db_id


async def write(text: str, title: str = "") -> Dict[str, Any]:
    """
    Create a new note page in Notion database
    
    Args:
        text: Note content
        title: Note title (defaults to first line of text)
        
    Returns:
        Dictionary with status and note info
    """
    if not NOTION_AVAILABLE:
        return {
            "status": "error",
            "result": None,
            "message": "Notion client not available. Install with: uv add notion-client"
        }
    
    if not NOTION_API_KEY or not NOTION_NOTES_DATABASE_ID:
        return {
            "status": "error",
            "result": None,
            "message": "Notion API key or notes database ID not configured. Set NOTION_API_KEY and NOTION_NOTES_DATABASE_ID in .env"
        }
    
    try:
        import httpx
        
        def _create_notion_page():
            # Use first line as title if not provided
            note_title = title if title else text.split('\n')[0][:100]
            
            # Create page properties (using Korean property names)
            properties = {
                "이름": {  # Korean: Name (Title)
                    "title": [
                        {
                            "text": {
                                "content": note_title
                            }
                        }
                    ]
                }
            }
            
            # Add content as tags if available (since database uses 태그 instead of 내용)
            if text and text != note_title:
                # Use first 100 chars of content as a tag
                content_preview = text[:100]
                properties["태그"] = {  # Korean: Tags
                    "multi_select": [
                        {"name": content_preview}
                    ]
                }
            
            # Create page using direct HTTP request
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            formatted_db_id = _format_database_id(NOTION_NOTES_DATABASE_ID)
            body = {
                "parent": {"database_id": formatted_db_id},
                "properties": properties
            }
            
            url = "https://api.notion.com/v1/pages"
            
            with httpx.Client() as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return response.json()
        
        response = await asyncio.to_thread(_create_notion_page)
        
        # Use first line as title if not provided
        note_title = title if title else text.split('\n')[0][:100]
        
        note = {
            "id": response["id"],
            "title": note_title,
            "content": text,
            "created_at": response.get("created_time", ""),
            "url": response.get("url", "")
        }
        
        return {
            "status": "ok",
            "result": note,
            "message": f"Note created in Notion: {note_title}"
        }
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return {
                "status": "error",
                "result": None,
                "message": "Notion database not found. Please check: 1) Database ID is correct, 2) Integration has access to the database"
            }
        return {
            "status": "error",
            "result": None,
            "message": f"Error creating Notion note: {error_msg}"
        }


async def list() -> Dict[str, Any]:
    """
    List all notes from Notion database
    
    Returns:
        Dictionary with status and notes list
    """
    if not NOTION_AVAILABLE:
        return {
            "status": "error",
            "result": None,
            "message": "Notion client not available. Install with: uv add notion-client"
        }
    
    if not NOTION_API_KEY or not NOTION_NOTES_DATABASE_ID:
        return {
            "status": "error",
            "result": None,
            "message": "Notion API key or notes database ID not configured. Set NOTION_API_KEY and NOTION_NOTES_DATABASE_ID in .env"
        }
    
    try:
        import httpx
        
        def _query_notion():
            # Query database using direct HTTP request
            body = {
                "sorts": [
                    {
                        "property": "생성일",  # Korean: Created
                        "direction": "descending"
                    }
                ]
            }
            
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            formatted_db_id = _format_database_id(NOTION_NOTES_DATABASE_ID)
            url = f"https://api.notion.com/v1/databases/{formatted_db_id}/query"
            
            with httpx.Client() as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return response.json()
        
        response = await asyncio.to_thread(_query_notion)
        
        # Parse results
        notes = []
        for page in response.get("results", []):
            properties = page.get("properties", {})
            
            # Extract title (Korean property name)
            title_prop = properties.get("이름") or properties.get("제목") or properties.get("Title") or properties.get("Name")
            title = ""
            if title_prop and title_prop.get("title"):
                title = "".join([t.get("plain_text", "") for t in title_prop["title"]])
            
            # Extract content from tags (Korean property name)
            tags_prop = properties.get("태그") or properties.get("Tags")
            content = ""
            if tags_prop and tags_prop.get("multi_select"):
                tags = [t.get("name", "") for t in tags_prop["multi_select"]]
                content = ", ".join(tags)
                # Truncate to 500 chars for list view
                if len(content) > 500:
                    content = content[:500] + "..."
            
            # Extract created time (Korean property name)
            created_prop = properties.get("생성일") or properties.get("Created")
            created_at = ""
            if created_prop and created_prop.get("created_time"):
                created_at = created_prop["created_time"]
            
            notes.append({
                "id": page["id"],
                "title": title,
                "content": content,
                "created_at": created_at,
                "url": page.get("url", "")
            })
        
        return {
            "status": "ok",
            "result": notes,
            "message": f"Found {len(notes)} notes from Notion"
        }
        
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return {
                "status": "error",
                "result": None,
                "message": "Notion database not found. Please check: 1) Database ID is correct, 2) Integration has access to the database"
            }
        return {
            "status": "error",
            "result": None,
            "message": f"Error listing Notion notes: {error_msg}"
        }
