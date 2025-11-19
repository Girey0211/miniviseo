"""
Session Manager - Manages conversation history per session
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
from utils.logger import get_logger

logger = get_logger()


class ConversationHistory:
    """Stores conversation history for a single session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict] = []
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.last_accessed = datetime.now()
        logger.debug(f"Session {self.session_id}: Added {role} message")
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation messages"""
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def get_context_for_llm(self, limit: int = 10) -> List[Dict]:
        """Get recent messages formatted for LLM context"""
        recent_messages = self.messages[-limit:]
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in recent_messages
        ]
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []
        logger.info(f"Session {self.session_id}: History cleared")


class SessionManager:
    """Manages multiple conversation sessions"""
    
    def __init__(self, session_timeout_minutes: int = 60):
        self.sessions: Dict[str, ConversationHistory] = {}
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task = None
        logger.info(f"SessionManager initialized (timeout: {session_timeout_minutes}m)")
    
    def get_or_create_session(self, session_id: str) -> ConversationHistory:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationHistory(session_id)
            logger.info(f"Created new session: {session_id}")
        else:
            self.sessions[session_id].last_accessed = datetime.now()
        
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[ConversationHistory]:
        """Get existing session"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = [
            sid for sid, session in self.sessions.items()
            if now - session.last_accessed > self.session_timeout
        ]
        
        for sid in expired:
            del self.sessions[sid]
            logger.info(f"Cleaned up expired session: {sid}")
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)
    
    async def start_cleanup_task(self, interval_minutes: int = 10):
        """Start background task to cleanup expired sessions"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_minutes * 60)
                self.cleanup_expired_sessions()
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Started session cleanup task (interval: {interval_minutes}m)")
    
    def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            logger.info("Stopped session cleanup task")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
