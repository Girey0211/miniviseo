"""
Notion Calendar MCP Tool - Calendar integration with Notion
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
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
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


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


def _parse_relative_date(date_str: str) -> str:
    """
    Parse relative date strings to ISO format
    
    Args:
        date_str: Date string (e.g., "오늘", "내일", "2024-01-01")
        
    Returns:
        ISO format date string (YYYY-MM-DD)
    """
    if date_str in ["오늘", "today", ""]:
        return datetime.now().strftime("%Y-%m-%d")
    elif date_str in ["내일", "tomorrow"]:
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_str in ["이번주", "this week"]:
        return datetime.now().strftime("%Y-%m-%d")
    else:
        return date_str


async def list_events(range_start: Optional[str] = None, range_end: Optional[str] = None) -> Dict[str, Any]:
    """
    List calendar events from Notion database
    
    Args:
        range_start: Optional start date filter (ISO format)
        range_end: Optional end date filter (ISO format)
        
    Returns:
        Dictionary with status and events list
    """
    if not NOTION_AVAILABLE:
        return {
            "status": "error",
            "result": None,
            "message": "Notion client not available. Install with: uv add notion-client"
        }
    
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        return {
            "status": "error",
            "result": None,
            "message": "Notion API key or database ID not configured. Set NOTION_API_KEY and NOTION_DATABASE_ID in .env"
        }
    
    try:
        import httpx
        
        def _query_notion():
            # Build filter for date range
            filter_conditions = []
            
            if range_start:
                filter_conditions.append({
                    "property": "Date",
                    "date": {
                        "on_or_after": range_start
                    }
                })
            
            if range_end:
                filter_conditions.append({
                    "property": "Date",
                    "date": {
                        "on_or_before": range_end
                    }
                })
            
            # Query database using direct HTTP request
            body = {
                "sorts": [
                    {
                        "property": "Date",
                        "direction": "ascending"
                    }
                ]
            }
            
            if filter_conditions:
                if len(filter_conditions) == 1:
                    body["filter"] = filter_conditions[0]
                else:
                    body["filter"] = {
                        "and": filter_conditions
                    }
            
            # Use httpx to make direct API call
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            formatted_db_id = _format_database_id(NOTION_DATABASE_ID)
            url = f"https://api.notion.com/v1/databases/{formatted_db_id}/query"
            
            with httpx.Client() as client:
                response = client.post(url, json=body, headers=headers)
                response.raise_for_status()
                return response.json()
        
        response = await asyncio.to_thread(_query_notion)
        
        # Parse results
        events = []
        for page in response.get("results", []):
            properties = page.get("properties", {})
            
            # Extract title
            title_prop = properties.get("Name") or properties.get("Title") or properties.get("이름")
            title = ""
            if title_prop and title_prop.get("title"):
                title = "".join([t.get("plain_text", "") for t in title_prop["title"]])
            
            # Extract date
            date_prop = properties.get("Date") or properties.get("날짜")
            date = ""
            time = ""
            if date_prop and date_prop.get("date"):
                date_info = date_prop["date"]
                date = date_info.get("start", "")
                # Extract time if datetime
                if "T" in date:
                    date, time = date.split("T")
                    time = time[:5]  # HH:MM
            
            # Extract description
            description_prop = properties.get("Description") or properties.get("설명")
            description = ""
            if description_prop and description_prop.get("rich_text"):
                description = "".join([t.get("plain_text", "") for t in description_prop["rich_text"]])
            
            events.append({
                "id": page["id"],
                "title": title,
                "date": date,
                "time": time,
                "description": description,
                "url": page.get("url", "")
            })
        
        return {
            "status": "ok",
            "result": events,
            "message": f"Found {len(events)} events from Notion"
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
            "message": f"Error listing Notion events: {error_msg}"
        }


async def add_event(title: str, date: str = "", time: str = "", description: str = "") -> Dict[str, Any]:
    """
    Add a calendar event to Notion database
    
    Args:
        title: Event title
        date: Event date (YYYY-MM-DD or relative like "오늘")
        time: Event time (HH:MM)
        description: Optional event description
        
    Returns:
        Dictionary with status and event info
    """
    if not NOTION_AVAILABLE:
        return {
            "status": "error",
            "result": None,
            "message": "Notion client not available. Install with: uv add notion-client"
        }
    
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        return {
            "status": "error",
            "result": None,
            "message": "Notion API key or database ID not configured. Set NOTION_API_KEY and NOTION_DATABASE_ID in .env"
        }
    
    try:
        import httpx
        
        def _create_notion_page():
            # Parse date
            parsed_date = _parse_relative_date(date)
            
            # Combine date and time for Notion
            if time:
                notion_date = f"{parsed_date}T{time}:00"
            else:
                notion_date = parsed_date
            
            # Create page properties
            properties = {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Date": {
                    "date": {
                        "start": notion_date
                    }
                }
            }
            
            # Add description if provided
            if description:
                properties["Description"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": description
                            }
                        }
                    ]
                }
            
            # Create page using direct HTTP request
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            formatted_db_id = _format_database_id(NOTION_DATABASE_ID)
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
        
        event = {
            "id": response["id"],
            "title": title,
            "date": parsed_date,
            "time": time,
            "description": description,
            "url": response.get("url", ""),
            "created_at": response.get("created_time", "")
        }
        
        return {
            "status": "ok",
            "result": event,
            "message": f"Event added to Notion: {title}"
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
            "message": f"Error adding Notion event: {error_msg}"
        }
