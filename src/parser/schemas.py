from pydantic import BaseModel
from typing import Dict, Optional, List


class AgentAction(BaseModel):
    """Single agent action to execute"""
    intent: str
    agent: str
    params: Dict[str, Optional[str]] = {}
    use_results_from: List[int] = []  # List of action indices to use results from (1-based)


class ParsedRequest(BaseModel):
    """Parsed request with multiple possible actions"""
    actions: List[AgentAction] = []
    raw_text: Optional[str] = None
