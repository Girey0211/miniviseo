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
    
    def test_create_history(self):
        """Test creating conversation history"""
        history = ConversationHistory("test-session")
        assert history.session_id == "test-session"
        assert len(history.messages) == 0
        assert isinstance(history.created_at, datetime)
    
    def test_add_message(self):
        """Test adding messages to history"""
        history = ConversationHistory("test-session")
        
        history.add_message("user", "안녕하세요")
        assert len(history.messages) == 1
        assert history.messages[0]["role"] == "user"
        assert history.messages[0]["content"] == "안녕하세요"
        
        history.add_message("assistant", "안녕하세요! 무엇을 도와드릴까요?")
        assert len(history.messages) == 2
    
    def test_add_message_with_metadata(self):
        """Test adding message with metadata"""
        history = ConversationHistory("test-session")
        
        metadata = {"intent": "greeting", "agent": "FallbackAgent"}
        history.add_message("assistant", "안녕하세요", metadata=metadata)
        
        assert history.messages[0]["metadata"] == metadata
    
    def test_get_messages(self):
        """Test getting all messages"""
        history = ConversationHistory("test-session")
        
        history.add_message("user", "메시지 1")
        history.add_message("assistant", "응답 1")
        history.add_message("user", "메시지 2")
        
        messages = history.get_messages()
        assert len(messages) == 3
    
    def test_get_messages_with_limit(self):
        """Test getting limited messages"""
        history = ConversationHistory("test-session")
        
        for i in range(10):
            history.add_message("user", f"메시지 {i}")
        
        recent = history.get_messages(limit=3)
        assert len(recent) == 3
        assert recent[0]["content"] == "메시지 7"
        assert recent[-1]["content"] == "메시지 9"
    
    def test_get_context_for_llm(self):
        """Test getting LLM context format"""
        history = ConversationHistory("test-session")
        
        history.add_message("user", "안녕하세요")
        history.add_message("assistant", "안녕하세요!")
        
        context = history.get_context_for_llm()
        assert len(context) == 2
        assert context[0] == {"role": "user", "content": "안녕하세요"}
        assert context[1] == {"role": "assistant", "content": "안녕하세요!"}
        assert "timestamp" not in context[0]
        assert "metadata" not in context[0]
    
    def test_get_context_for_llm_with_limit(self):
        """Test getting limited LLM context"""
        history = ConversationHistory("test-session")
        
        for i in range(20):
            history.add_message("user", f"메시지 {i}")
        
        context = history.get_context_for_llm(limit=5)
        assert len(context) == 5
    
    def test_clear_history(self):
        """Test clearing conversation history"""
        history = ConversationHistory("test-session")
        
        history.add_message("user", "메시지 1")
        history.add_message("assistant", "응답 1")
        assert len(history.messages) == 2
        
        history.clear()
        assert len(history.messages) == 0
    
    def test_last_accessed_updates(self):
        """Test that last_accessed updates on message add"""
        history = ConversationHistory("test-session")
        initial_time = history.last_accessed
        
        import time
        time.sleep(0.01)
        
        history.add_message("user", "메시지")
        assert history.last_accessed > initial_time


class TestSessionManager:
    """Test SessionManager class"""
    
    def test_create_manager(self):
        """Test creating session manager"""
        manager = SessionManager()
        assert manager.get_active_session_count() == 0
    
    def test_get_or_create_session(self):
        """Test getting or creating session"""
        manager = SessionManager()
        
        session1 = manager.get_or_create_session("session-1")
        assert session1.session_id == "session-1"
        assert manager.get_active_session_count() == 1
        
        # Get same session again
        session2 = manager.get_or_create_session("session-1")
        assert session1 is session2
        assert manager.get_active_session_count() == 1
    
    def test_get_session(self):
        """Test getting existing session"""
        manager = SessionManager()
        
        manager.get_or_create_session("session-1")
        
        session = manager.get_session("session-1")
        assert session is not None
        assert session.session_id == "session-1"
        
        # Non-existent session
        session = manager.get_session("non-existent")
        assert session is None
    
    def test_delete_session(self):
        """Test deleting session"""
        manager = SessionManager()
        
        manager.get_or_create_session("session-1")
        assert manager.get_active_session_count() == 1
        
        deleted = manager.delete_session("session-1")
        assert deleted is True
        assert manager.get_active_session_count() == 0
        
        # Delete non-existent session
        deleted = manager.delete_session("non-existent")
        assert deleted is False
    
    def test_multiple_sessions(self):
        """Test managing multiple sessions"""
        manager = SessionManager()
        
        session1 = manager.get_or_create_session("user-1")
        session2 = manager.get_or_create_session("user-2")
        session3 = manager.get_or_create_session("user-3")
        
        assert manager.get_active_session_count() == 3
        
        session1.add_message("user", "메시지 1")
        session2.add_message("user", "메시지 2")
        
        assert len(session1.messages) == 1
        assert len(session2.messages) == 1
        assert len(session3.messages) == 0
    
    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions"""
        manager = SessionManager(session_timeout_minutes=1)
        
        # Create sessions
        session1 = manager.get_or_create_session("session-1")
        session2 = manager.get_or_create_session("session-2")
        
        # Manually set session1 as expired
        session1.last_accessed = datetime.now() - timedelta(minutes=2)
        
        assert manager.get_active_session_count() == 2
        
        manager.cleanup_expired_sessions()
        
        assert manager.get_active_session_count() == 1
        assert manager.get_session("session-1") is None
        assert manager.get_session("session-2") is not None
    
    def test_session_timeout_configuration(self):
        """Test session timeout configuration"""
        manager = SessionManager(session_timeout_minutes=30)
        assert manager.session_timeout == timedelta(minutes=30)
        
        manager2 = SessionManager(session_timeout_minutes=120)
        assert manager2.session_timeout == timedelta(minutes=120)
    
    def test_get_active_session_count(self):
        """Test getting active session count"""
        manager = SessionManager()
        
        assert manager.get_active_session_count() == 0
        
        manager.get_or_create_session("session-1")
        assert manager.get_active_session_count() == 1
        
        manager.get_or_create_session("session-2")
        manager.get_or_create_session("session-3")
        assert manager.get_active_session_count() == 3
        
        manager.delete_session("session-2")
        assert manager.get_active_session_count() == 2


class TestSessionIntegration:
    """Integration tests for session management"""
    
    def test_conversation_flow(self):
        """Test complete conversation flow"""
        manager = SessionManager()
        session = manager.get_or_create_session("user-123")
        
        # User asks to create note
        session.add_message("user", "오늘 한 일 메모해줘: 프로젝트 완료")
        session.add_message(
            "assistant", 
            "메모를 작성했습니다.",
            metadata={"intent": "write_note", "agent": "NoteAgent"}
        )
        
        # User asks to list notes
        session.add_message("user", "내 메모 목록 보여줘")
        session.add_message(
            "assistant",
            "메모 목록입니다: ...",
            metadata={"intent": "list_notes", "agent": "NoteAgent"}
        )
        
        assert len(session.messages) == 4
        
        # Get context for LLM
        context = session.get_context_for_llm()
        assert len(context) == 4
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
    
    def test_session_persistence_across_requests(self):
        """Test session persists across multiple requests"""
        manager = SessionManager()
        
        # First request
        session1 = manager.get_or_create_session("user-456")
        session1.add_message("user", "안녕하세요")
        session1.add_message("assistant", "안녕하세요!")
        
        # Second request (same session)
        session2 = manager.get_or_create_session("user-456")
        assert session1 is session2
        assert len(session2.messages) == 2
        
        session2.add_message("user", "메모 작성해줘")
        assert len(session2.messages) == 3
    
    def test_isolated_sessions(self):
        """Test that sessions are isolated from each other"""
        manager = SessionManager()
        
        session_a = manager.get_or_create_session("user-a")
        session_b = manager.get_or_create_session("user-b")
        
        session_a.add_message("user", "User A 메시지")
        session_b.add_message("user", "User B 메시지")
        
        assert len(session_a.messages) == 1
        assert len(session_b.messages) == 1
        assert session_a.messages[0]["content"] == "User A 메시지"
        assert session_b.messages[0]["content"] == "User B 메시지"
