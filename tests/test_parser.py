import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.request_parser import RequestParser, parse_request
from parser.schemas import ParsedRequest


@pytest.fixture
def parser():
    """Create RequestParser instance for testing"""
    return RequestParser()


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    def _create_response(content: str):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = content
        return mock_response
    return _create_response


class TestRequestParser:
    """Test cases for RequestParser"""
    
    @pytest.mark.asyncio
    async def test_parse_list_files_request(self, parser, mock_openai_response):
        """Test parsing file list request"""
        # Mock OpenAI response
        response_json = '{"intent": "list_files", "agent": "FileAgent", "params": {"path": "Downloads"}}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("downloads 폴더 파일 보여줘")
            
            assert isinstance(result, ParsedRequest)
            assert result.intent == "list_files"
            assert result.agent == "FileAgent"
            assert result.params.get("path") == "Downloads"
            assert result.raw_text == "downloads 폴더 파일 보여줘"
    
    @pytest.mark.asyncio
    async def test_parse_read_file_request(self, parser, mock_openai_response):
        """Test parsing file read request"""
        response_json = '{"intent": "read_file", "agent": "FileAgent", "params": {"path": "documents/report.pdf"}}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("documents에서 report.pdf 열어줘")
            
            assert result.intent == "read_file"
            assert result.agent == "FileAgent"
            assert "path" in result.params
    
    @pytest.mark.asyncio
    async def test_parse_write_note_request(self, parser, mock_openai_response):
        """Test parsing note write request"""
        response_json = '{"intent": "write_note", "agent": "NoteAgent", "params": {"text": "오늘은 프로젝트 설정 완료"}}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("오늘 한 일 메모해줘: 프로젝트 설정 완료")
            
            assert result.intent == "write_note"
            assert result.agent == "NoteAgent"
            assert "text" in result.params or "content" in result.params
    
    @pytest.mark.asyncio
    async def test_parse_calendar_add_request(self, parser, mock_openai_response):
        """Test parsing calendar add request"""
        response_json = '{"intent": "calendar_add", "agent": "CalendarAgent", "params": {"time": "09:00", "title": "회의"}}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("오늘 오전 9시에 회의 잡아줘")
            
            assert result.intent == "calendar_add"
            assert result.agent == "CalendarAgent"
            assert "time" in result.params or "title" in result.params
    
    @pytest.mark.asyncio
    async def test_parse_web_search_request(self, parser, mock_openai_response):
        """Test parsing web search request"""
        response_json = '{"intent": "web_search", "agent": "WebAgent", "params": {"query": "파이썬 최신 뉴스"}}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("파이썬 최신 뉴스 검색해줘")
            
            assert result.intent == "web_search"
            assert result.agent == "WebAgent"
            assert "query" in result.params or "url" in result.params
    
    @pytest.mark.asyncio
    async def test_parse_list_notes_request(self, parser, mock_openai_response):
        """Test parsing notes list request"""
        response_json = '{"intent": "list_notes", "agent": "NoteAgent", "params": {}}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("notes 전체 알려줘")
            
            assert result.intent == "list_notes"
            assert result.agent == "NoteAgent"
    
    @pytest.mark.asyncio
    async def test_parse_calendar_list_request(self, parser, mock_openai_response):
        """Test parsing calendar list request"""
        response_json = '{"intent": "calendar_list", "agent": "CalendarAgent", "params": {}}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("이번주 일정 알려줘")
            
            assert result.intent == "calendar_list"
            assert result.agent == "CalendarAgent"
    
    @pytest.mark.asyncio
    async def test_parse_invalid_json_fallback(self, parser, mock_openai_response):
        """Test fallback when JSON parsing fails"""
        # Return invalid JSON
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response("This is not valid JSON")
            
            result = await parser.parse_request("알 수 없는 요청")
            
            assert result.intent == "unknown"
            assert result.agent == "FallbackAgent"
            assert result.raw_text == "알 수 없는 요청"
    
    @pytest.mark.asyncio
    async def test_parse_api_error_fallback(self, parser):
        """Test fallback when API call fails"""
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = await parser.parse_request("테스트 요청")
            
            assert result.intent == "unknown"
            assert result.agent == "FallbackAgent"
            assert "error" in result.params
    
    @pytest.mark.asyncio
    async def test_parse_request_convenience_function(self, mock_openai_response):
        """Test convenience function parse_request"""
        response_json = '{"intent": "list_files", "agent": "FileAgent", "params": {"path": "Downloads"}}'
        
        with patch('src.parser.request_parser.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response(response_json))
            
            result = await parse_request("파일 보여줘")
            
            assert isinstance(result, ParsedRequest)
            assert result.intent == "list_files"


class TestParsedRequestSchema:
    """Test ParsedRequest Pydantic model"""
    
    def test_parsed_request_creation(self):
        """Test creating ParsedRequest with valid data"""
        request = ParsedRequest(
            intent="list_files",
            agent="FileAgent",
            params={"path": "Downloads"},
            raw_text="파일 보여줘"
        )
        
        assert request.intent == "list_files"
        assert request.agent == "FileAgent"
        assert request.params["path"] == "Downloads"
        assert request.raw_text == "파일 보여줘"
    
    def test_parsed_request_default_params(self):
        """Test ParsedRequest with default empty params"""
        request = ParsedRequest(
            intent="unknown",
            agent="FallbackAgent"
        )
        
        assert request.params == {}
        assert request.raw_text is None
    
    def test_parsed_request_optional_fields(self):
        """Test ParsedRequest with optional fields"""
        request = ParsedRequest(
            intent="list_notes",
            agent="NoteAgent",
            params={}
        )
        
        assert request.raw_text is None
