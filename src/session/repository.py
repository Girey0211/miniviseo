"""
Session Repository - Abstract interface for session storage
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from datetime import datetime


class SessionRepository(ABC):
    """Abstract base class for session storage"""
    
    @abstractmethod
    async def save_session(
        self, 
        session_id: str, 
        created_at: datetime, 
        last_accessed: datetime,
        expires_at: datetime
    ) -> bool:
        """Save or update session metadata"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session metadata"""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all its messages"""
        pass
    
    @abstractmethod
    async def get_all_sessions(self) -> List[Dict]:
        """Get all sessions"""
        pass
    
    @abstractmethod
    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        timestamp: datetime,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Save a message to session"""
        pass
    
    @abstractmethod
    async def get_messages(
        self, 
        session_id: str, 
        page: int = 0,
        page_size: int = 10
    ) -> List[Dict]:
        """Get messages for a session with pagination
        
        Args:
            session_id: Session ID
            page: Page number (0-based, 0 = most recent)
            page_size: Number of messages per page
        """
        pass
    
    @abstractmethod
    async def delete_messages(self, session_id: str) -> bool:
        """Delete all messages for a session"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, expiry_time: datetime) -> int:
        """Delete sessions older than expiry_time"""
        pass
    
    @abstractmethod
    async def get_session_count(self) -> int:
        """Get total number of active sessions"""
        pass
    
    @abstractmethod
    async def get_total_message_count(self) -> int:
        """Get total number of messages across all sessions"""
        pass
