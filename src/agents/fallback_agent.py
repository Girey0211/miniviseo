"""
FallbackAgent - Handles unknown or unsupported requests
"""
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase


class FallbackAgent(AgentBase):
    """Agent for handling unknown or unsupported requests"""
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle unknown requests
        
        Args:
            params: Dictionary with request parameters
            
        Returns:
            Dictionary with status and helpful message
        """
        # Extract debug info
        debug_info = {
            "params": params,
            "agent": self.get_agent_name()
        }
        
        return {
            "status": "ok",
            "result": debug_info,
            "message": "무슨 요청인지 잘 모르겠어요. 다시 한번 말씀해주시겠어요?"
        }
