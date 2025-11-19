"""
Tests for Session Management
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from session import SessionManager, ConversationHistory


class TestConversationHistory:
    """Test ConversationHistory class"""
    
    @pytest.mark.asyncio
    async def test_create_history(self):
        """Test creating conversation history"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        assert history.session_id == "test-session"
        assert isinstance(history.created_at, datetime)
    
    @pytest.mark.asyncio
    async def test_add_message(self):
        """Test adding messages to history"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        
        await history.add_message("user", "안녕하세요")
        messages = await history.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "안녕하세요"
        
        await history.add_message("assistant", "안녕하세요! 무엇을 도와드릴까요?")
        messages = await history.get_messages()
        assert len(messages) == 2
    
    @pytest.mark.asyncio
    async def test_add_message_with_metadata(self):
        """Test adding message with metadata"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        
        metadata = {"intent": "greeting", "agent": "FallbackAgent"}
        await history.add_message("assistant", "안녕하세요", metadata=metadata)
        
        messages = await history.get_messages()
        assert messages[0]["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_get_messages(self):
        """Test getting all messages"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        
        await history.add_message("user", "메시지 1")
        await history.add_message("assistant", "응답 1")
        await history.add_message("user", "메시지 2")
        
        messages = await history.get_messages()
        assert len(messages) == 3
    
    @pytest.mark.asyncio
    async def test_get_messages_with_pagination(self):
        """Test getting messages with pagination"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        
        for i in range(10):
            await history.add_message("user", f"메시지 {i}")
        
        # Page 0 (most recent 3)
        recent = await history.get_messages(page=0, page_size=3)
        assert len(recent) == 3
        assert recent[0]["content"] == "메시지 7"
        assert recent[-1]["content"] == "메시지 9"
        
        # Page 1 (next 3)
        next_page = await history.get_messages(page=1, page_size=3)
        assert len(next_page) == 3
        assert next_page[0]["content"] == "메시지 4"
        assert next_page[-1]["content"] == "메시지 6"
    
    @pytest.mark.asyncio
    async def test_get_context_for_llm(self):
        """Test getting LLM context format"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        
        await history.add_message("user", "안녕하세요")
        await history.add_message("assistant", "안녕하세요!")
        
        context = await history.get_context_for_llm()
        assert len(context) == 2
        assert context[0] == {"role": "user", "content": "안녕하세요"}
        assert context[1] == {"role": "assistant", "content": "안녕하세요!"}
        assert "timestamp" not in context[0]
        assert "metadata" not in context[0]
    
    @pytest.mark.asyncio
    async def test_get_context_for_llm_with_limit(self):
        """Test getting limited LLM context"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        
        for i in range(20):
            await history.add_message("user", f"메시지 {i}")
        
        # Should get most recent 5 messages
        context = await history.get_context_for_llm(limit=5)
        assert len(context) == 5
        assert context[0]["content"] == "메시지 15"
        assert context[-1]["content"] == "메시지 19"
    
    @pytest.mark.asyncio
    async def test_clear_history(self):
        """Test clearing conversation history"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        
        await history.add_message("user", "메시지 1")
        await history.add_message("assistant", "응답 1")
        messages = await history.get_messages()
        assert len(messages) == 2
        
        await history.clear()
        messages = await history.get_messages()
        assert len(messages) == 0
    
    @pytest.mark.asyncio
    async def test_last_accessed_updates(self):
        """Test that last_accessed updates on message add"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        history = ConversationHistory("test-session", repo)
        initial_time = history.last_accessed
        
        import time
        time.sleep(0.01)
        
        await history.add_message("user", "메시지")
        assert history.last_accessed > initial_time


class TestSessionManager:
    """Test SessionManager class"""
    
    @pytest.mark.asyncio
    async def test_create_manager(self):
        """Test creating session manager"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        count = await manager.get_active_session_count()
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_get_or_create_session(self):
        """Test getting or creating session"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        
        session1 = await manager.get_or_create_session("session-1")
        assert session1.session_id == "session-1"
        count = await manager.get_active_session_count()
        assert count == 1
        
        # Get same session again
        session2 = await manager.get_or_create_session("session-1")
        assert session1 is session2
        count = await manager.get_active_session_count()
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_get_session(self):
        """Test getting existing session"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        
        await manager.get_or_create_session("session-1")
        
        session = await manager.get_session("session-1")
        assert session is not None
        assert session.session_id == "session-1"
        
        # Non-existent session
        session = await manager.get_session("non-existent")
        assert session is None
    
    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting session"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        
        await manager.get_or_create_session("session-1")
        count = await manager.get_active_session_count()
        assert count == 1
        
        deleted = await manager.delete_session("session-1")
        assert deleted is True
        count = await manager.get_active_session_count()
        assert count == 0
        
        # Delete non-existent session
        deleted = await manager.delete_session("non-existent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test managing multiple sessions"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        
        session1 = await manager.get_or_create_session("user-1")
        session2 = await manager.get_or_create_session("user-2")
        session3 = await manager.get_or_create_session("user-3")
        
        count = await manager.get_active_session_count()
        assert count == 3
        
        await session1.add_message("user", "메시지 1")
        await session2.add_message("user", "메시지 2")
        
        messages1 = await session1.get_messages()
        messages2 = await session2.get_messages()
        messages3 = await session3.get_messages()
        
        assert len(messages1) == 1
        assert len(messages2) == 1
        assert len(messages3) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions based on expires_at"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo, session_expiry_days=7)
        
        # Create sessions
        session1 = await manager.get_or_create_session("session-1")
        session2 = await manager.get_or_create_session("session-2")
        
        # Manually set session1 as expired in repository
        now = datetime.now()
        expired_time = now - timedelta(days=1)  # Expired yesterday
        await repo.save_session("session-1", session1.created_at, now, expired_time)
        
        count = await manager.get_active_session_count()
        assert count == 2
        
        await manager.cleanup_expired_sessions()
        
        count = await manager.get_active_session_count()
        assert count == 1
        
        # Session should be removed from memory cache
        assert "session-1" not in manager.sessions
        assert "session-2" in manager.sessions
    
    @pytest.mark.asyncio
    async def test_session_expiry_configuration(self):
        """Test session expiry configuration"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo, session_expiry_days=7)
        assert manager.session_expiry_days == 7
        
        repo2 = SQLiteSessionRepository(db_path=":memory:")
        manager2 = SessionManager(repository=repo2, session_expiry_days=30)
        assert manager2.session_expiry_days == 30
    
    @pytest.mark.asyncio
    async def test_get_active_session_count(self):
        """Test getting active session count"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        
        count = await manager.get_active_session_count()
        assert count == 0
        
        await manager.get_or_create_session("session-1")
        count = await manager.get_active_session_count()
        assert count == 1
        
        await manager.get_or_create_session("session-2")
        await manager.get_or_create_session("session-3")
        count = await manager.get_active_session_count()
        assert count == 3
        
        await manager.delete_session("session-2")
        count = await manager.get_active_session_count()
        assert count == 2


class TestSessionIntegration:
    """Integration tests for session management"""
    
    @pytest.mark.asyncio
    async def test_conversation_flow(self):
        """Test complete conversation flow"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        session = await manager.get_or_create_session("user-123")
        
        # User asks to create note
        await session.add_message("user", "오늘 한 일 메모해줘: 프로젝트 완료")
        await session.add_message(
            "assistant", 
            "메모를 작성했습니다.",
            metadata={"intent": "write_note", "agent": "NoteAgent"}
        )
        
        # User asks to list notes
        await session.add_message("user", "내 메모 목록 보여줘")
        await session.add_message(
            "assistant",
            "메모 목록입니다: ...",
            metadata={"intent": "list_notes", "agent": "NoteAgent"}
        )
        
        messages = await session.get_messages()
        assert len(messages) == 4
        
        # Get context for LLM
        context = await session.get_context_for_llm()
        assert len(context) == 4
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_session_persistence_across_requests(self):
        """Test session persists across multiple requests"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        
        # First request
        session1 = await manager.get_or_create_session("user-456")
        await session1.add_message("user", "안녕하세요")
        await session1.add_message("assistant", "안녕하세요!")
        
        # Second request (same session)
        session2 = await manager.get_or_create_session("user-456")
        assert session1 is session2
        messages = await session2.get_messages()
        assert len(messages) == 2
        
        await session2.add_message("user", "메모 작성해줘")
        messages = await session2.get_messages()
        assert len(messages) == 3
    
    @pytest.mark.asyncio
    async def test_isolated_sessions(self):
        """Test that sessions are isolated from each other"""
        from session.sqlite_repository import SQLiteSessionRepository
        repo = SQLiteSessionRepository(db_path=":memory:")
        manager = SessionManager(repository=repo)
        
        session_a = await manager.get_or_create_session("user-a")
        session_b = await manager.get_or_create_session("user-b")
        
        await session_a.add_message("user", "User A 메시지")
        await session_b.add_message("user", "User B 메시지")
        
        messages_a = await session_a.get_messages()
        messages_b = await session_b.get_messages()
        
        assert len(messages_a) == 1
        assert len(messages_b) == 1
        assert messages_a[0]["content"] == "User A 메시지"
        assert messages_b[0]["content"] == "User B 메시지"
