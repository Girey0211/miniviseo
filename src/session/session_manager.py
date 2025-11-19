"""
Session Manager - Manages conversation history per session
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from session.repository import SessionRepository
from session.sqlite_repository import SQLiteSessionRepository
from utils.logger import get_logger

logger = get_logger()


class ConversationHistory:
    """Stores conversation history for a single session"""
    
    def __init__(self, session_id: str, repository: SessionRepository):
        self.session_id = session_id
        self.repository = repository
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self._messages_cache: Optional[List[Dict]] = None
    
    async def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history"""
        timestamp = datetime.now()
        expires_at = timestamp + timedelta(days=7)  # 7일 후 만료
        
        # Ensure session exists in repository first and update expiry
        await self.repository.save_session(
            session_id=self.session_id,
            created_at=self.created_at,
            last_accessed=timestamp,
            expires_at=expires_at
        )
        
        # Save message to repository
        await self.repository.save_message(
            session_id=self.session_id,
            role=role,
            content=content,
            timestamp=timestamp,
            metadata=metadata
        )
        
        # Update session access time
        self.last_accessed = timestamp
        
        # Invalidate cache
        self._messages_cache = None
        
        logger.debug(f"Session {self.session_id}: Added {role} message")
    
    async def get_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Get conversation messages"""
        messages = await self.repository.get_messages(self.session_id, limit=limit)
        return messages
    
    async def get_context_for_llm(self, limit: int = 10) -> List[Dict]:
        """Get recent messages formatted for LLM context"""
        messages = await self.get_messages(limit=limit)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]
    
    async def clear(self):
        """Clear conversation history"""
        await self.repository.delete_messages(self.session_id)
        self._messages_cache = None
        logger.info(f"Session {self.session_id}: History cleared")
    
    async def get_message_count(self) -> int:
        """Get number of messages in this session"""
        messages = await self.get_messages()
        return len(messages)


class SessionManager:
    """Manages multiple conversation sessions with persistent storage"""
    
    def __init__(
        self, 
        repository: Optional[SessionRepository] = None,
        session_expiry_days: int = 7
    ):
        self.repository = repository or SQLiteSessionRepository()
        self.sessions: Dict[str, ConversationHistory] = {}
        self.session_expiry_days = session_expiry_days
        self._cleanup_task = None
        logger.info(f"SessionManager initialized (expiry: {session_expiry_days} days)")
    
    async def get_or_create_session(self, session_id: str) -> ConversationHistory:
        """Get existing session or create new one"""
        now = datetime.now()
        expires_at = now + timedelta(days=self.session_expiry_days)
        
        # Check in-memory cache first
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_accessed = now
            # 세션 사용 시마다 만료 기한 갱신 (7일 연장)
            await self.repository.save_session(
                session_id=session_id,
                created_at=session.created_at,
                last_accessed=session.last_accessed,
                expires_at=expires_at
            )
            return session
        
        # Check if session exists in repository
        session_data = await self.repository.get_session(session_id)
        
        if session_data:
            # Restore from repository
            session = ConversationHistory(session_id, self.repository)
            session.created_at = session_data["created_at"]
            session.last_accessed = now
            self.sessions[session_id] = session
            
            # 세션 복원 시에도 만료 기한 갱신
            await self.repository.save_session(
                session_id=session_id,
                created_at=session.created_at,
                last_accessed=session.last_accessed,
                expires_at=expires_at
            )
            
            logger.info(f"Restored session from storage: {session_id}")
        else:
            # Create new session
            session = ConversationHistory(session_id, self.repository)
            self.sessions[session_id] = session
            
            await self.repository.save_session(
                session_id=session_id,
                created_at=session.created_at,
                last_accessed=session.last_accessed,
                expires_at=expires_at
            )
            
            logger.info(f"Created new session: {session_id}")
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[ConversationHistory]:
        """Get existing session"""
        # Check in-memory cache
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        # Check repository
        session_data = await self.repository.get_session(session_id)
        if session_data:
            session = ConversationHistory(session_id, self.repository)
            session.created_at = session_data["created_at"]
            session.last_accessed = session_data["last_accessed"]
            self.sessions[session_id] = session
            return session
        
        return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # Remove from repository
        deleted = await self.repository.delete_session(session_id)
        
        if deleted:
            logger.info(f"Deleted session: {session_id}")
        
        return deleted
    
    async def cleanup_expired_sessions(self):
        """Remove expired sessions (expires_at < now)"""
        now = datetime.now()
        
        # Cleanup from repository (sessions where expires_at < now)
        deleted_count = await self.repository.cleanup_expired_sessions(now)
        
        # Cleanup from memory cache - remove sessions that are in deleted list
        # We need to check repository to see which sessions still exist
        expired_in_memory = []
        for sid in list(self.sessions.keys()):
            session_data = await self.repository.get_session(sid)
            if not session_data:
                # Session was deleted from repository
                expired_in_memory.append(sid)
                del self.sessions[sid]
        
        if deleted_count > 0 or expired_in_memory:
            logger.info(f"Cleaned up {deleted_count} expired sessions from storage, {len(expired_in_memory)} from cache")
    
    async def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return await self.repository.get_session_count()
    
    async def get_total_message_count(self) -> int:
        """Get total number of messages across all sessions"""
        return await self.repository.get_total_message_count()
    
    async def start_cleanup_task(self, interval_minutes: int = 10):
        """Start background task to cleanup expired sessions"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_minutes * 60)
                await self.cleanup_expired_sessions()
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Started session cleanup task (interval: {interval_minutes}m)")
    
    def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            logger.info("Stopped session cleanup task")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(repository: Optional[SessionRepository] = None) -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(repository=repository)
    return _session_manager
