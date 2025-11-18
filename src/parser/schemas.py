from pydantic import BaseModel
from typing import Dict, Optional


class ParsedRequest(BaseModel):
    intent: str
    agent: str
    params: Dict[str, Optional[str]] = {}
    raw_text: Optional[str] = None
