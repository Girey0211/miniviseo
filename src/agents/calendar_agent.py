"""
CalendarAgent - Handles calendar operations using Notion
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL


class CalendarAgent(AgentBase):
    """Agent for calendar operations using Notion Calendar"""
    
    def __init__(self, mcp_client=None, llm_client=None):
        super().__init__(mcp_client, llm_client)
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
    
    async def _extract_event_data(self, raw_input: str) -> Dict[str, str]:
        """
        Extract structured event data from natural language input using LLM
        
        Args:
            raw_input: Natural language description of the event
            
        Returns:
            Dictionary with title, date, time, description (raw_input as description)
        """
        try:
            from datetime import timezone, timedelta
            
            # Use KST (UTC+9)
            kst = timezone(timedelta(hours=9))
            today = datetime.now(kst).strftime("%Y-%m-%d")
            current_time = datetime.now(kst).strftime("%H:%M")
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a helpful assistant that extracts calendar event information from Korean text.
Today's date is {today} (KST - Korea Standard Time, UTC+9).
Current time is {current_time} (KST).

Extract the following information and return ONLY a JSON object:
{{
  "title": "concise event title (max 50 characters)",
  "date": "YYYY-MM-DD format",
  "time": "HH:MM format (24-hour, KST)"
}}

Rules:
- Generate a concise, descriptive title (max 50 characters) that summarizes the event
- If date is relative (오늘, 내일, 다음주 월요일), convert to YYYY-MM-DD based on KST
- If time is not specified, use empty string
- If time is relative (오후 3시 = 15:00, 오전 9시 = 09:00), convert to 24-hour format
- All times should be in KST (Korea Standard Time)"""
                    },
                    {
                        "role": "user",
                        "content": f"Extract event information and generate a title from: {raw_input}"
                    }
                ],
                temperature=0.3,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            event_data = json.loads(content)
            
            # Use raw_input as description (full content)
            return {
                "title": event_data.get("title", "")[:50],  # Limit title length
                "date": event_data.get("date", ""),
                "time": event_data.get("time", ""),
                "description": raw_input  # Use original input as description
            }
            
        except Exception as e:
            # Fallback: use raw input as title
            return {
                "title": raw_input[:100],
                "date": "",
                "time": "",
                "description": ""
            }
    
    async def _extract_date_range(self, raw_input: str) -> Dict[str, str]:
        """
        Extract date range from natural language input using LLM
        
        Args:
            raw_input: Natural language description of date range
            
        Returns:
            Dictionary with range_start and range_end
        """
        try:
            from datetime import timezone, timedelta
            
            # Use KST (UTC+9)
            kst = timezone(timedelta(hours=9))
            today = datetime.now(kst).strftime("%Y-%m-%d")
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a helpful assistant that extracts date ranges from Korean text.
Today's date is {today} (KST - Korea Standard Time, UTC+9).

Extract date range and return ONLY a JSON object:
{{
  "range_start": "YYYY-MM-DD or empty",
  "range_end": "YYYY-MM-DD or empty"
}}

Rules:
- Convert relative dates (오늘, 이번주, 다음달) to YYYY-MM-DD based on KST
- If only one date mentioned, use it for range_start
- If no specific date, return empty strings
- All dates should be in KST (Korea Standard Time)"""
                    },
                    {
                        "role": "user",
                        "content": f"Extract date range from: {raw_input}"
                    }
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            date_range = json.loads(content)
            
            return {
                "range_start": date_range.get("range_start", ""),
                "range_end": date_range.get("range_end", "")
            }
            
        except Exception as e:
            # Fallback: no date range
            return {
                "range_start": "",
                "range_end": ""
            }
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle calendar operation requests
        
        Supported operations:
        - calendar_list: List calendar events
        - calendar_add: Add a new event
        
        Args:
            params: Dictionary with raw text, structured event details, or previous_results
            
        Returns:
            Dictionary with status, result, and message
        """
        if self.mcp is None:
            return self._create_error_response("MCP client not available")
        
        # Determine action
        action = params.get("action", "list")
        intent = params.get("intent", "")
        
        try:
            if action in ["calendar_add", "add"] or intent == "calendar_add":
                # Add event - extract data from raw input using LLM
                raw_text = params.get("text") or params.get("raw_text", "")
                
                # Debug: log params to identify the issue
                from utils.logger import get_logger
                logger = get_logger()
                logger.debug(f"CalendarAgent params: {params}")
                logger.debug(f"CalendarAgent raw_text type: {type(raw_text)}, value: {raw_text}")
                
                # Check if there are previous results to incorporate (e.g., web search results)
                previous_results = params.get("previous_results", [])
                additional_info = ""
                
                if previous_results:
                    for prev in previous_results:
                        # Skip FallbackAgent results (they contain debug info, not useful content)
                        if prev.get("agent") == "FallbackAgent":
                            continue
                        
                        prev_result = prev.get("result", {})
                        if prev_result.get("status") == "ok":
                            prev_data = prev_result.get("result", "")
                            
                            # Handle different result formats
                            if isinstance(prev_data, str):
                                additional_info = prev_data
                                break
                            elif isinstance(prev_data, dict):
                                # For web search results with summary
                                if "summary" in prev_data:
                                    additional_info = prev_data["summary"]
                                    # Optionally add sources
                                    if "sources" in prev_data:
                                        sources_text = "\n\n참고 링크:\n"
                                        for source in prev_data["sources"]:
                                            sources_text += f"- {source['title']}: {source['url']}\n"
                                        additional_info += sources_text
                                    break
                                # Skip debug info from FallbackAgent
                                elif "params" in prev_data and "agent" in prev_data:
                                    continue
                                else:
                                    additional_info = str(prev_data)
                                    break
                
                # If structured data already provided, use it; otherwise extract from text
                if params.get("title"):
                    event_data = {
                        "title": params.get("title", ""),
                        "date": params.get("date", ""),
                        "time": params.get("time", ""),
                        "description": params.get("description", "") or additional_info
                    }
                elif raw_text:
                    event_data = await self._extract_event_data(raw_text)
                    # Append additional info from previous results to description
                    if additional_info:
                        if event_data.get("description"):
                            event_data["description"] = f"{event_data['description']}\n\n{additional_info}"
                        else:
                            event_data["description"] = additional_info
                else:
                    return self._create_error_response("Event information is required")
                
                if not event_data["title"]:
                    return self._create_error_response("Event title is required")
                
                # Log event data for debugging
                from utils.logger import get_logger
                logger = get_logger()
                logger.debug(f"Creating calendar event with data: {event_data}")
                
                result = await self.mcp.call("notion_calendar", "add_event", event_data)
                
                # Log result for debugging
                logger.debug(f"Calendar event creation result: {result}")
            else:
                # List events - extract date range from raw input using LLM
                raw_text = params.get("text") or params.get("raw_text", "")
                
                # If structured data already provided, use it; otherwise extract from text
                if params.get("range_start") or params.get("start_date"):
                    date_range = {
                        "range_start": params.get("range_start") or params.get("start_date"),
                        "range_end": params.get("range_end") or params.get("end_date")
                    }
                elif raw_text:
                    date_range = await self._extract_date_range(raw_text)
                else:
                    date_range = {"range_start": None, "range_end": None}
                
                result = await self.mcp.call("notion_calendar", "list_events", date_range)
            
            return result
            
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger()
            logger.error(f"Error in CalendarAgent.handle: {str(e)}", exc_info=True)
            return self._create_error_response(
                message=f"Error handling calendar operation",
                error=e
            )
