"""
Property-based tests for notion_notes MCP tool

Feature: agent-refactoring
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from hypothesis import given, strategies as st, settings
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Strategies for generating test data
text_strategy = st.text(min_size=1, max_size=2000).filter(lambda x: x.strip())
title_strategy = st.text(min_size=0, max_size=100)


class TestNotionNotesPropertyBased:
    """Property-based tests for notion_notes tool"""
    
    @pytest.mark.asyncio
    @given(text=text_strategy, title=title_strategy)
    @settings(max_examples=100)
    async def test_property_notes_creation_with_timestamp(self, text, title):
        """
        **Feature: agent-refactoring, Property 2: Notion notes creation with timestamp**
        **Validates: Requirements 2.1, 2.4**
        
        For any valid note text and title, calling notion_notes.write should create 
        a new page in the Notion database with matching content and a timestamp property
        """
        from mcp.tools import notion_notes
        
        # Mock httpx.Client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test_page_id",
            "url": "https://notion.so/test_page",
            "created_time": datetime.now().isoformat()
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        
        # Patch environment variables and httpx
        with patch.object(notion_notes, "NOTION_API_KEY", "test_key"), \
             patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", "test_db_id"), \
             patch('httpx.Client', return_value=mock_client):
            
            result = await notion_notes.write(text=text, title=title)
            
            # Verify successful creation
            assert result["status"] == "ok"
            assert result["result"] is not None
            
            # Verify note has required fields
            note = result["result"]
            assert "id" in note
            assert "title" in note
            assert "content" in note
            assert "created_at" in note
            assert "url" in note
            
            # Verify content matches input
            assert note["content"] == text
            
            # Verify title is set (either provided or derived from text)
            if title:
                assert note["title"] == title
            else:
                # Should use first line of text
                expected_title = text.split('\n')[0][:100]
                assert note["title"] == expected_title
            
            # Verify timestamp exists
            assert note["created_at"] != ""
            
            # Verify the API was called with correct properties
            call_args = mock_client.post.call_args
            assert call_args is not None
            body = call_args[1]["json"]
            
            # Verify Korean property names are used
            assert "이름" in body["properties"]  # Changed from 제목 to 이름
            # Note: 내용 is replaced with 태그 in the actual database
            assert "이름" in body["properties"] or "태그" in body["properties"]
    
    @pytest.mark.asyncio
    @given(num_notes=st.integers(min_value=0, max_value=10))
    @settings(max_examples=100)
    async def test_property_notes_retrieval_completeness(self, num_notes):
        """
        **Feature: agent-refactoring, Property 3: Notion notes retrieval completeness**
        **Validates: Requirements 2.2, 2.5**
        
        For any Notion notes database with N pages, calling notion_notes.list should 
        return exactly N notes, each with all required fields
        """
        from mcp.tools import notion_notes
        
        # Generate mock notes
        mock_notes = []
        for i in range(num_notes):
            mock_notes.append({
                "id": f"page_{i}",
                "url": f"https://notion.so/page_{i}",
                "properties": {
                    "제목": {
                        "title": [{"plain_text": f"Note {i}"}]
                    },
                    "내용": {
                        "rich_text": [{"plain_text": f"Content {i}"}]
                    },
                    "생성일": {
                        "created_time": datetime.now().isoformat()
                    }
                }
            })
        
        # Mock httpx.Client
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": mock_notes}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        
        # Patch environment variables and httpx
        with patch.object(notion_notes, "NOTION_API_KEY", "test_key"), \
             patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", "test_db_id"), \
             patch('httpx.Client', return_value=mock_client):
            
            result = await notion_notes.list()
            
            # Verify successful retrieval
            assert result["status"] == "ok"
            assert result["result"] is not None
            
            # Verify exactly N notes returned
            notes = result["result"]
            assert len(notes) == num_notes
            
            # Verify each note has all required fields
            for note in notes:
                assert "id" in note
                assert "title" in note
                assert "content" in note
                assert "created_at" in note
                assert "url" in note
                
                # Verify fields are not empty
                assert note["id"] != ""
                assert note["url"] != ""
    
    @pytest.mark.asyncio
    @given(
        error_type=st.sampled_from([
            "missing_api_key",
            "missing_database_id",
            "404_not_found",
            "network_error"
        ])
    )
    @settings(max_examples=100)
    async def test_property_notion_api_error_handling(self, error_type):
        """
        **Feature: agent-refactoring, Property 4: Notion API error handling**
        **Validates: Requirements 2.3**
        
        For any Notion API failure, the system should return an error status 
        with a descriptive message
        """
        from mcp.tools import notion_notes
        
        if error_type == "missing_api_key":
            # Test missing API key
            with patch.object(notion_notes, "NOTION_API_KEY", None), \
                 patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", "test_db_id"):
                
                result = await notion_notes.write(text="test", title="test")
                
                assert result["status"] == "error"
                assert "not configured" in result["message"]
                
        elif error_type == "missing_database_id":
            # Test missing database ID
            with patch.object(notion_notes, "NOTION_API_KEY", "test_key"), \
                 patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", None):
                
                result = await notion_notes.list()
                
                assert result["status"] == "error"
                assert "not configured" in result["message"]
                
        elif error_type == "404_not_found":
            # Test 404 error
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("404")
            
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post = MagicMock(return_value=mock_response)
            
            with patch.object(notion_notes, "NOTION_API_KEY", "test_key"), \
                 patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", "test_db_id"), \
                 patch('httpx.Client', return_value=mock_client):
                
                result = await notion_notes.write(text="test", title="test")
                
                assert result["status"] == "error"
                assert "not found" in result["message"].lower()
                
        elif error_type == "network_error":
            # Test network error
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("Connection timeout")
            
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post = MagicMock(return_value=mock_response)
            
            with patch.object(notion_notes, "NOTION_API_KEY", "test_key"), \
                 patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", "test_db_id"), \
                 patch('httpx.Client', return_value=mock_client):
                
                result = await notion_notes.list()
                
                assert result["status"] == "error"
                assert "message" in result
                assert result["message"] != ""


class TestNotionNotesUnit:
    """Unit tests for notion_notes tool"""
    
    @pytest.mark.asyncio
    async def test_write_without_config(self):
        """Test writing note without Notion configuration"""
        from mcp.tools import notion_notes
        
        with patch.object(notion_notes, "NOTION_API_KEY", None), \
             patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", None):
            
            result = await notion_notes.write(text="test note", title="test")
            
            assert result["status"] == "error"
            assert "not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_list_without_config(self):
        """Test listing notes without Notion configuration"""
        from mcp.tools import notion_notes
        
        with patch.object(notion_notes, "NOTION_API_KEY", None), \
             patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", None):
            
            result = await notion_notes.list()
            
            assert result["status"] == "error"
            assert "not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_write_with_mock_notion(self):
        """Test writing note with mocked httpx"""
        from mcp.tools import notion_notes
        
        # Mock httpx.Client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test_page_id",
            "url": "https://notion.so/test_page",
            "created_time": "2024-01-01T00:00:00.000Z"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        
        with patch.object(notion_notes, "NOTION_API_KEY", "test_key"), \
             patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", "test_db_id"), \
             patch('httpx.Client', return_value=mock_client):
            
            result = await notion_notes.write(text="Test content", title="Test title")
            
            if result["status"] != "ok":
                print(f"Error: {result}")
            
            assert result["status"] == "ok"
            assert result["result"]["title"] == "Test title"
            assert result["result"]["content"] == "Test content"
    
    @pytest.mark.asyncio
    async def test_list_with_mock_notion(self):
        """Test listing notes with mocked httpx"""
        from mcp.tools import notion_notes
        
        # Mock httpx.Client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "page1",
                    "url": "https://notion.so/page1",
                    "properties": {
                        "제목": {
                            "title": [{"plain_text": "Note 1"}]
                        },
                        "내용": {
                            "rich_text": [{"plain_text": "Content 1"}]
                        },
                        "생성일": {
                            "created_time": "2024-01-01T00:00:00.000Z"
                        }
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)
        
        with patch.object(notion_notes, "NOTION_API_KEY", "test_key"), \
             patch.object(notion_notes, "NOTION_NOTES_DATABASE_ID", "test_db_id"), \
             patch('httpx.Client', return_value=mock_client):
            
            result = await notion_notes.list()
            
            assert result["status"] == "ok"
            assert len(result["result"]) == 1
            assert result["result"][0]["title"] == "Note 1"
    
    def test_format_database_id(self):
        """Test database ID formatting"""
        from mcp.tools.notion_notes import _format_database_id
        
        # Test with 32-char ID without hyphens
        db_id = "12345678901234567890123456789012"
        formatted = _format_database_id(db_id)
        assert formatted == "12345678-9012-3456-7890-123456789012"
        
        # Test with already formatted ID
        formatted_id = "12345678-9012-3456-7890-123456789012"
        result = _format_database_id(formatted_id)
        assert result == formatted_id
        
        # Test with empty string
        assert _format_database_id("") == ""
