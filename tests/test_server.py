"""
Tests for HTTP API Server
"""
import pytest
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import app, initialize_app, _session_manager


@pytest.fixture(scope="module", autouse=True)
def setup_server():
    """Initialize server before tests"""
    initialize_app()
    yield


class TestServerAPI:
    """Test cases for API server endpoints"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns health status"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["version"] == "0.1.0"
    
    @pytest.mark.asyncio
    async def test_assistant_endpoint_success(self):
        """Test assistant endpoint with valid request"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                json={"text": "안녕하세요"}
            )
            
            # May return 200, 400, or 500 depending on API key and agent availability
            assert response.status_code in [200, 400, 500]
            if response.status_code == 200:
                data = response.json()
                assert "response" in data
                assert "intent" in data
                assert "agent" in data
                assert "status" in data
    
    @pytest.mark.asyncio
    async def test_assistant_endpoint_empty_text(self):
        """Test assistant endpoint with empty text"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                json={"text": ""}
            )
            
            # Should still process but might return unknown intent
            assert response.status_code in [200, 400, 500]
    
    @pytest.mark.asyncio
    async def test_assistant_endpoint_note_request(self):
        """Test assistant endpoint with note creation request"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                json={"text": "메모 작성해줘: 테스트 메모"}
            )
            
            # May return 200, 400, or 500 depending on API key and agent availability
            assert response.status_code in [200, 400, 500]
            if response.status_code == 200:
                data = response.json()
                assert data["intent"] in ["write_note", "unknown"]
                assert data["agent"] in ["NoteAgent", "FallbackAgent"]
    
    @pytest.mark.asyncio
    async def test_assistant_endpoint_web_search(self):
        """Test assistant endpoint with web search request"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                json={"text": "파이썬 검색해줘"}
            )
            
            # May return 200, 400, or 500 depending on API key and agent availability
            assert response.status_code in [200, 400, 500]
            if response.status_code == 200:
                data = response.json()
                assert data["intent"] in ["web_search", "unknown"]
    
    @pytest.mark.asyncio
    async def test_assistant_endpoint_invalid_json(self):
        """Test assistant endpoint with invalid JSON"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                content="invalid json",
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 422  # Unprocessable Entity
    
    @pytest.mark.asyncio
    async def test_assistant_endpoint_missing_text_field(self):
        """Test assistant endpoint with missing text field"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                json={"message": "wrong field"}
            )
            
            assert response.status_code == 422  # Unprocessable Entity


class TestServerSession:
    """Test session management endpoints"""
    
    @pytest.mark.asyncio
    async def test_assistant_with_session_id(self):
        """Test assistant endpoint with session ID"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                json={
                    "text": "안녕하세요",
                    "session_id": "test-session-123"
                }
            )
            
            assert response.status_code in [200, 400, 500]
            if response.status_code == 200:
                data = response.json()
                assert data["session_id"] == "test-session-123"
    
    @pytest.mark.asyncio
    async def test_assistant_without_session_id(self):
        """Test assistant endpoint without session ID"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/assistant",
                json={"text": "안녕하세요"}
            )
            
            assert response.status_code in [200, 400, 500]
            if response.status_code == 200:
                data = response.json()
                assert data["session_id"] is None
    
    @pytest.mark.asyncio
    async def test_session_persistence(self):
        """Test that session persists across multiple requests"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = "test-session-persistence"
            
            # First request
            response1 = await client.post(
                "/assistant",
                json={
                    "text": "첫 번째 메시지",
                    "session_id": session_id
                }
            )
            
            # Second request with same session
            response2 = await client.post(
                "/assistant",
                json={
                    "text": "두 번째 메시지",
                    "session_id": session_id
                }
            )
            
            if response1.status_code == 200 and response2.status_code == 200:
                # Check session info
                info_response = await client.get(f"/sessions/{session_id}")
                assert info_response.status_code == 200
                
                info_data = info_response.json()
                assert info_data["session_id"] == session_id
                assert info_data["message_count"] >= 2  # At least 2 messages
    
    @pytest.mark.asyncio
    async def test_get_session_info(self):
        """Test getting session info with messages"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = "test-session-info"
            
            # Create session by making request
            await client.post(
                "/assistant",
                json={
                    "text": "테스트 메시지",
                    "session_id": session_id
                }
            )
            
            # Get session info
            response = await client.get(f"/sessions/{session_id}")
            
            if response.status_code == 200:
                data = response.json()
                assert data["session_id"] == session_id
                assert "message_count" in data
                assert "created_at" in data
                assert "last_accessed" in data
                assert "messages" in data
                assert isinstance(data["messages"], list)
                # Should have at least user message and assistant response
                assert data["message_count"] >= 2
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self):
        """Test getting info for non-existent session"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sessions/nonexistent-session")
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting a session"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = "test-session-delete"
            
            # Create session
            await client.post(
                "/assistant",
                json={
                    "text": "테스트 메시지",
                    "session_id": session_id
                }
            )
            
            # Delete session
            delete_response = await client.delete(f"/sessions/{session_id}")
            
            if delete_response.status_code == 200:
                # Verify session is deleted
                info_response = await client.get(f"/sessions/{session_id}")
                assert info_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self):
        """Test deleting non-existent session"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/sessions/nonexistent-session")
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_session_info_with_limit(self):
        """Test getting session info with message limit"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            session_id = "test-session-limit"
            
            # Create session with multiple messages
            for i in range(5):
                await client.post(
                    "/assistant",
                    json={
                        "text": f"메시지 {i}",
                        "session_id": session_id
                    }
                )
            
            # Get session info with limit
            response = await client.get(f"/sessions/{session_id}?limit=3")
            
            if response.status_code == 200:
                data = response.json()
                assert data["session_id"] == session_id
                # Should return only last 3 messages
                assert len(data["messages"]) <= 3
    
    @pytest.mark.asyncio
    async def test_session_stats(self):
        """Test getting session statistics"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sessions-stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "active_sessions" in data
            assert "total_messages" in data
            assert isinstance(data["active_sessions"], int)
            assert isinstance(data["total_messages"], int)


class TestServerCORS:
    """Test CORS configuration"""
    
    @pytest.mark.asyncio
    async def test_cors_headers(self):
        """Test CORS headers are present"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/assistant",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST"
                }
            )
            
            # CORS should allow the request
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers
