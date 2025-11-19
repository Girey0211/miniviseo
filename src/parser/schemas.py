from pydantic import BaseModel
from typing import Dict, Optional, List


class AgentAction(BaseModel):
    """Single agent action to execute"""
    intent: str
    agent: str
    params: Dict[str, Optional[str]] = {}


class ParsedRequest(BaseModel):
    """Parsed request with multiple possible actions"""
    actions: List[AgentAction] = []
    raw_text: Optional[str] = None
