"""
Notes MCP Tool - Note management with JSON storage
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import NOTES_FILE


async def write(text: str, title: str = "") -> Dict[str, Any]:
    """
    Write a new note
    
    Args:
        text: Note content
        title: Optional note title
        
    Returns:
        Dictionary with status and note info
    """
    try:
        # Ensure data directory exists
        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing notes
        if NOTES_FILE.exists():
            with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                notes = json.load(f)
        else:
            notes = []
        
        # Create new note
        note = {
            "id": len(notes) + 1,
            "title": title,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Append note
        notes.append(note)
        
        # Save notes
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "ok",
            "result": note,
            "message": f"Note saved (ID: {note['id']})"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error writing note: {str(e)}"
        }


async def list() -> Dict[str, Any]:
    """
    List all notes
    
    Returns:
        Dictionary with status and notes list
    """
    try:
        # Check if notes file exists
        if not NOTES_FILE.exists():
            return {
                "status": "ok",
                "result": [],
                "message": "No notes found"
            }
        
        # Load notes
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            notes = json.load(f)
        
        return {
            "status": "ok",
            "result": notes,
            "message": f"Found {len(notes)} notes"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error listing notes: {str(e)}"
        }
