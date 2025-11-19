"""
Tests for SQLite Session Repository
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from session.sqlite_repository import SQLiteSessionRepository


class TestSQLiteRepository:
    """Test SQLite repository implementation"""
    
    @pytest.mark.asyncio
    async def test_save_and_get_session(self):
        """Test saving and retrieving session"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session_id = "test-session"
        created_at = datetime.now()
        last_accessed = datetime.now()
        
        # Save session
        result = await repo.save_session(session_id, created_at, last_accessed)
        assert result is True
        
        # Get session
        session = await repo.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert isinstance(session["created_at"], datetime)
        assert isinstance(session["last_accessed"], datetime)
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self):
        """Test getting non-existent session"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session = await repo.get_session("nonexistent")
        assert session is None
    
    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting session"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session_id = "test-session"
        await repo.save_session(session_id, datetime.now(), datetime.now())
        
        # Delete session
        deleted = await repo.delete_session(session_id)
        assert deleted is True
        
        # Verify deleted
        session = await repo.get_session(session_id)
        assert session is None
        
        # Delete non-existent
        deleted = await repo.delete_session("nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_save_and_get_messages(self):
        """Test saving and retrieving messages"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session_id = "test-session"
        await repo.save_session(session_id, datetime.now(), datetime.now())
        
        # Save messages
        await repo.save_message(
            session_id=session_id,
            role="user",
            content="Hello",
            timestamp=datetime.now()
        )
        
        await repo.save_message(
            session_id=session_id,
            role="assistant",
            content="Hi there!",
            timestamp=datetime.now(),
            metadata={"intent": "greeting"}
        )
        
        # Get messages
        messages = await repo.get_messages(session_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["metadata"] == {"intent": "greeting"}
    
    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self):
        """Test getting limited messages"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session_id = "test-session"
        await repo.save_session(session_id, datetime.now(), datetime.now())
        
        # Save 10 messages
        for i in range(10):
            await repo.save_message(
                session_id=session_id,
                role="user",
                content=f"Message {i}",
                timestamp=datetime.now()
            )
        
        # Get last 3 messages
        messages = await repo.get_messages(session_id, limit=3)
        assert len(messages) == 3
        assert messages[0]["content"] == "Message 7"
        assert messages[-1]["content"] == "Message 9"
    
    @pytest.mark.asyncio
    async def test_delete_messages(self):
        """Test deleting messages"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session_id = "test-session"
        await repo.save_session(session_id, datetime.now(), datetime.now())
        
        await repo.save_message(session_id, "user", "Hello", datetime.now())
        await repo.save_message(session_id, "assistant", "Hi", datetime.now())
        
        # Delete messages
        result = await repo.delete_messages(session_id)
        assert result is True
        
        # Verify deleted
        messages = await repo.get_messages(session_id)
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_cascade_delete(self):
        """Test that deleting session deletes messages"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session_id = "test-session"
        await repo.save_session(session_id, datetime.now(), datetime.now())
        
        await repo.save_message(session_id, "user", "Hello", datetime.now())
        await repo.save_message(session_id, "assistant", "Hi", datetime.now())
        
        # Delete session
        await repo.delete_session(session_id)
        
        # Messages should be deleted too
        messages = await repo.get_messages(session_id)
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        # Create sessions with different access times
        now = datetime.now()
        
        await repo.save_session("session-1", now, now - timedelta(hours=2))
        await repo.save_session("session-2", now, now - timedelta(minutes=30))
        await repo.save_session("session-3", now, now)
        
        # Cleanup sessions older than 1 hour
        expiry_time = now - timedelta(hours=1)
        deleted_count = await repo.cleanup_expired_sessions(expiry_time)
        
        assert deleted_count == 1
        
        # Verify
        session1 = await repo.get_session("session-1")
        session2 = await repo.get_session("session-2")
        session3 = await repo.get_session("session-3")
        
        assert session1 is None
        assert session2 is not None
        assert session3 is not None
    
    @pytest.mark.asyncio
    async def test_get_session_count(self):
        """Test getting session count"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        count = await repo.get_session_count()
        assert count == 0
        
        await repo.save_session("session-1", datetime.now(), datetime.now())
        await repo.save_session("session-2", datetime.now(), datetime.now())
        
        count = await repo.get_session_count()
        assert count == 2
        
        await repo.delete_session("session-1")
        
        count = await repo.get_session_count()
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_get_total_message_count(self):
        """Test getting total message count"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        count = await repo.get_total_message_count()
        assert count == 0
        
        # Create sessions with messages
        await repo.save_session("session-1", datetime.now(), datetime.now())
        await repo.save_message("session-1", "user", "Hello", datetime.now())
        await repo.save_message("session-1", "assistant", "Hi", datetime.now())
        
        await repo.save_session("session-2", datetime.now(), datetime.now())
        await repo.save_message("session-2", "user", "Test", datetime.now())
        
        count = await repo.get_total_message_count()
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_get_all_sessions(self):
        """Test getting all sessions"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        sessions = await repo.get_all_sessions()
        assert len(sessions) == 0
        
        # Create sessions
        await repo.save_session("session-1", datetime.now(), datetime.now())
        await repo.save_session("session-2", datetime.now(), datetime.now())
        await repo.save_session("session-3", datetime.now(), datetime.now())
        
        sessions = await repo.get_all_sessions()
        assert len(sessions) == 3
        assert all("session_id" in s for s in sessions)
        assert all("created_at" in s for s in sessions)
        assert all("last_accessed" in s for s in sessions)
    
    @pytest.mark.asyncio
    async def test_update_session_access_time(self):
        """Test updating session access time"""
        repo = SQLiteSessionRepository(db_path=":memory:")
        
        session_id = "test-session"
        created_at = datetime.now()
        first_access = datetime.now()
        
        await repo.save_session(session_id, created_at, first_access)
        
        # Update access time
        import time
        time.sleep(0.01)
        second_access = datetime.now()
        await repo.save_session(session_id, created_at, second_access)
        
        # Verify updated
        session = await repo.get_session(session_id)
        assert session["last_accessed"] > first_access
