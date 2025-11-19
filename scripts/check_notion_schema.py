#!/usr/bin/env python3
"""
Notion Database Schema Checker
Check the properties of your Notion Calendar database
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv()

import httpx

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_CALENDAR_DATABASE_ID = os.getenv("NOTION_CALENDAR_DATABASE_ID")


def format_database_id(db_id: str) -> str:
    """Format database ID to UUID format with hyphens"""
    if not db_id:
        return db_id
    db_id = db_id.replace("-", "")
    if len(db_id) == 32:
        return f"{db_id[:8]}-{db_id[8:12]}-{db_id[12:16]}-{db_id[16:20]}-{db_id[20:]}"
    return db_id


def check_database_schema():
    """Check Notion database schema"""
    if not NOTION_API_KEY:
        print("❌ NOTION_API_KEY not found in .env")
        return
    
    if not NOTION_CALENDAR_DATABASE_ID:
        print("❌ NOTION_CALENDAR_DATABASE_ID not found in .env")
        return
    
    print(f"✅ API Key found: {NOTION_API_KEY[:20]}...")
    print(f"✅ Database ID: {NOTION_CALENDAR_DATABASE_ID}")
    print()
    
    # Get database schema
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
    }
    
    formatted_db_id = format_database_id(NOTION_CALENDAR_DATABASE_ID)
    url = f"https://api.notion.com/v1/databases/{formatted_db_id}"
    
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return
            
            data = response.json()
            properties = data.get("properties", {})
            
            print("📋 Database Properties:")
            print("=" * 60)
            
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type", "unknown")
                print(f"  • {prop_name}: {prop_type}")
            
            print()
            print("=" * 60)
            print()
            print("✅ Required properties for Calendar:")
            print("  • 제목 (title)")
            print("  • 날짜 (date)")
            print("  • 설명 (rich_text) - optional")
            print()
            
            # Check if required properties exist
            has_title = False
            has_date = False
            has_description = False
            
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type", "")
                if prop_type == "title":
                    has_title = True
                    if prop_name != "제목":
                        print(f"⚠️  Title property name is '{prop_name}', expected '제목'")
                if prop_name == "날짜" and prop_type == "date":
                    has_date = True
                if prop_name == "설명" and prop_type == "rich_text":
                    has_description = True
            
            print()
            print("Status:")
            print(f"  {'✅' if has_title else '❌'} Title property (type: title)")
            print(f"  {'✅' if has_date else '❌'} 날짜 property (type: date)")
            print(f"  {'✅' if has_description else '⚠️ '} 설명 property (type: rich_text) - optional")
            
            if not has_title or not has_date:
                print()
                print("❌ Missing required properties!")
                print("Please add the missing properties to your Notion database.")
            else:
                print()
                print("✅ All required properties found!")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    check_database_schema()
