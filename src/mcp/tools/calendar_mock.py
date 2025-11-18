"""
Calendar Mock MCP Tool - Mock calendar with JSON storage
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import CALENDAR_FILE


async def list_events(range_start: Optional[str] = None, range_end: Optional[str] = None) -> Dict[str, Any]:
    """
    List calendar events
    
    Args:
        range_start: Optional start date filter (ISO format)
        range_end: Optional end date filter (ISO format)
        
    Returns:
        Dictionary with status and events list
    """
    try:
        # Check if calendar file exists
        if not CALENDAR_FILE.exists():
            return {
                "status": "ok",
                "result": [],
                "message": "No events found"
            }
        
        # Load events
        with open(CALENDAR_FILE, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        # Filter by date range if provided
        if range_start or range_end:
            filtered_events = []
            for event in events:
                event_date = event.get("date", "")
                
                if range_start and event_date < range_start:
                    continue
                if range_end and event_date > range_end:
                    continue
                
                filtered_events.append(event)
            
            events = filtered_events
        
        return {
            "status": "ok",
            "result": events,
            "message": f"Found {len(events)} events"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error listing events: {str(e)}"
        }


async def add_event(title: str, date: str = "", time: str = "", description: str = "") -> Dict[str, Any]:
    """
    Add a calendar event
    
    Args:
        title: Event title
        date: Event date (YYYY-MM-DD or relative like "오늘")
        time: Event time (HH:MM)
        description: Optional event description
        
    Returns:
        Dictionary with status and event info
    """
    try:
        # Ensure data directory exists
        CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing events
        if CALENDAR_FILE.exists():
            with open(CALENDAR_FILE, 'r', encoding='utf-8') as f:
                events = json.load(f)
        else:
            events = []
        
        # Parse date if relative
        if date in ["오늘", "today", ""]:
            date = datetime.now().strftime("%Y-%m-%d")
        elif date in ["내일", "tomorrow"]:
            from datetime import timedelta
            date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Create new event
        event = {
            "id": len(events) + 1,
            "title": title,
            "date": date,
            "time": time,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        
        # Append event
        events.append(event)
        
        # Save events
        with open(CALENDAR_FILE, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "ok",
            "result": event,
            "message": f"Event added (ID: {event['id']})"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error adding event: {str(e)}"
        }
