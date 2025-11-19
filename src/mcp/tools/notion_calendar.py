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
NOTION_CALENDAR_DATABASE_ID = os.getenv("NOTION_CALENDAR_DATABASE_ID")


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
    
    if not NOTION_API_KEY or not NOTION_CALENDAR_DATABASE_ID:
        return {
            "status": "error",
            "result": None,
            "message": "Notion API key or calendar database ID not configured. Set NOTION_API_KEY and NOTION_CALENDAR_DATABASE_ID in .env"
        }
    
    try:
        import httpx
        
        def _query_notion():
            # Build filter for date range
            filter_conditions = []
            
            if range_start:
                filter_conditions.append({
                    "property": "날짜",  # Korean property name
                    "date": {
                        "on_or_after": range_start
                    }
                })
            
            if range_end:
                filter_conditions.append({
                    "property": "날짜",  # Korean property name
                    "date": {
                        "on_or_before": range_end
                    }
                })
            
            # Query database using direct HTTP request
            # Try to sort by date property (support both Korean and English names)
            body = {}
            
            # Only add sorts if we're not filtering (Notion API limitation)
            if not filter_conditions:
                body["sorts"] = [
                    {
                        "property": "날짜",  # Korean property name
                        "direction": "ascending"
                    }
                ]
            
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
            
            formatted_db_id = _format_database_id(NOTION_CALENDAR_DATABASE_ID)
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
            
            # Extract title (Korean property name)
            title_prop = properties.get("이름") or properties.get("Name") or properties.get("Title")
            title = ""
            if title_prop and title_prop.get("title"):
                title = "".join([t.get("plain_text", "") for t in title_prop["title"]])
            
            # Extract date (Korean property name)
            date_prop = properties.get("날짜") or properties.get("Date")
            date = ""
            time = ""
            if date_prop and date_prop.get("date"):
                date_info = date_prop["date"]
                date = date_info.get("start", "")
                # Extract time if datetime
                if "T" in date:
                    date, time = date.split("T")
                    time = time[:5]  # HH:MM
            
            # Extract tags (Korean property name)
            tags_prop = properties.get("태그") or properties.get("Tags")
            description = ""
            if tags_prop and tags_prop.get("multi_select"):
                tags = [t.get("name", "") for t in tags_prop["multi_select"]]
                description = ", ".join(tags)
            
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
    
    if not NOTION_API_KEY or not NOTION_CALENDAR_DATABASE_ID:
        return {
            "status": "error",
            "result": None,
            "message": "Notion API key or calendar database ID not configured. Set NOTION_API_KEY and NOTION_CALENDAR_DATABASE_ID in .env"
        }
    
    try:
        import httpx
        
        def _create_notion_page():
            # Parse date
            parsed_date = _parse_relative_date(date)
            
            # Combine date and time for Notion with KST timezone
            if time:
                # Add KST timezone offset (+09:00) to prevent UTC conversion
                notion_date = f"{parsed_date}T{time}:00+09:00"
            else:
                notion_date = parsed_date
            
            # Prepare headers for API calls
            headers = {
                "Authorization": f"Bearer {NOTION_API_KEY}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            # Get database schema to find the correct property names
            formatted_db_id = _format_database_id(NOTION_CALENDAR_DATABASE_ID)
            schema_url = f"https://api.notion.com/v1/databases/{formatted_db_id}"
            
            with httpx.Client() as schema_client:
                schema_response = schema_client.get(schema_url, headers=headers)
                schema_response.raise_for_status()
                schema_data = schema_response.json()
                db_properties = schema_data.get("properties", {})
            
            # Find the title property name (could be '제목', '이름', 'Name', etc.)
            title_prop_name = None
            date_prop_name = "날짜"  # Default
            description_prop_name = None
            
            for prop_name, prop_data in db_properties.items():
                prop_type = prop_data.get("type", "")
                if prop_type == "title":
                    title_prop_name = prop_name
                elif prop_type == "date" and prop_name in ["날짜", "Date"]:
                    date_prop_name = prop_name
                elif prop_type == "rich_text" and prop_name in ["설명", "Description", "내용"]:
                    description_prop_name = prop_name
            
            if not title_prop_name:
                raise ValueError("No title property found in database")
            
            # Log warning if description property not found but description provided
            if description and not description_prop_name:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                from utils.logger import get_logger
                logger = get_logger()
                logger.warning(f"Description provided but no rich_text property found in database. Description will be ignored: {description[:100]}...")
                logger.warning("To save descriptions, add a '설명' (Rich Text) property to your Notion Calendar database.")
            
            # Create page properties using discovered property names
            properties = {
                title_prop_name: {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                date_prop_name: {
                    "date": {
                        "start": notion_date
                    }
                }
            }
            
            # Add description if provided and property exists
            if description and description_prop_name:
                properties[description_prop_name] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": description[:2000]  # Notion limit
                            }
                        }
                    ]
                }
            
            # Create page using direct HTTP request (headers already defined above)
            body = {
                "parent": {"database_id": formatted_db_id},
                "properties": properties
            }
            
            url = "https://api.notion.com/v1/pages"
            
            with httpx.Client() as client:
                # Log request for debugging
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                from utils.logger import get_logger
                logger = get_logger()
                logger.debug(f"Notion API request URL: {url}")
                logger.debug(f"Notion API request body: {body}")
                
                response = client.post(url, json=body, headers=headers)
                
                logger.debug(f"Notion API response status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Notion API error response: {response.text}")
                
                response.raise_for_status()
                return response.json()
        
        response = await asyncio.to_thread(_create_notion_page)
        
        # Parse date for response
        final_date = _parse_relative_date(date) if date else ""
        
        event = {
            "id": response["id"],
            "title": title,
            "date": final_date,
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
        elif "400" in error_msg:
            return {
                "status": "error",
                "result": None,
                "message": f"Notion API error (400 Bad Request). Please check your database properties. Expected properties: '제목' (Title), '날짜' (Date), '설명' (Rich Text). Error: {error_msg}"
            }
        return {
            "status": "error",
            "result": None,
            "message": f"Error adding Notion event: {error_msg}"
        }
