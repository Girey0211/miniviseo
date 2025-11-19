import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.request_parser import RequestParser, parse_request
from parser.schemas import ParsedRequest, AgentAction


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
    async def test_parse_single_action_request(self, parser, mock_openai_response):
        """Test parsing single action request"""
        # Mock OpenAI response with new format
        response_json = '{"actions": [{"intent": "write_note", "agent": "NoteAgent", "params": {"text": "테스트 메모"}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("메모 작성해줘")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 1
            assert result.actions[0].intent == "write_note"
            assert result.actions[0].agent == "NoteAgent"
            assert result.raw_text == "메모 작성해줘"
    
    @pytest.mark.asyncio
    async def test_parse_write_note_request(self, parser, mock_openai_response):
        """Test parsing note write request"""
        response_json = '{"actions": [{"intent": "write_note", "agent": "NoteAgent", "params": {"text": "오늘은 프로젝트 설정 완료"}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("오늘 한 일 메모해줘: 프로젝트 설정 완료")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "write_note"
            assert result.actions[0].agent == "NoteAgent"
            assert "text" in result.actions[0].params
    
    @pytest.mark.asyncio
    async def test_parse_calendar_add_request(self, parser, mock_openai_response):
        """Test parsing calendar add request"""
        response_json = '{"actions": [{"intent": "calendar_add", "agent": "CalendarAgent", "params": {"time": "09:00", "title": "회의"}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("오늘 오전 9시에 회의 잡아줘")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "calendar_add"
            assert result.actions[0].agent == "CalendarAgent"
    
    @pytest.mark.asyncio
    async def test_parse_web_search_request(self, parser, mock_openai_response):
        """Test parsing web search request"""
        response_json = '{"actions": [{"intent": "web_search", "agent": "WebAgent", "params": {"query": "파이썬 최신 뉴스"}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("파이썬 최신 뉴스 검색해줘")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "web_search"
            assert result.actions[0].agent == "WebAgent"
            assert "query" in result.actions[0].params
    
    @pytest.mark.asyncio
    async def test_parse_list_notes_request(self, parser, mock_openai_response):
        """Test parsing notes list request"""
        response_json = '{"actions": [{"intent": "list_notes", "agent": "NoteAgent", "params": {}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("notes 전체 알려줘")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "list_notes"
            assert result.actions[0].agent == "NoteAgent"
    
    @pytest.mark.asyncio
    async def test_parse_korean_memo_keyword(self, parser, mock_openai_response):
        """Test parsing Korean '메모' keyword to NoteAgent"""
        response_json = '{"actions": [{"intent": "write_note", "agent": "NoteAgent", "params": {"text": "테스트 메모"}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("메모 작성해줘: 테스트 메모")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "write_note"
            assert result.actions[0].agent == "NoteAgent"
    
    @pytest.mark.asyncio
    async def test_parse_korean_memo_list_keyword(self, parser, mock_openai_response):
        """Test parsing Korean '메모 목록' keyword to NoteAgent"""
        response_json = '{"actions": [{"intent": "list_notes", "agent": "NoteAgent", "params": {}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("메모 목록 보여줘")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "list_notes"
            assert result.actions[0].agent == "NoteAgent"
    
    @pytest.mark.asyncio
    async def test_parse_korean_note_keyword(self, parser, mock_openai_response):
        """Test parsing Korean '노트' keyword to NoteAgent"""
        response_json = '{"actions": [{"intent": "write_note", "agent": "NoteAgent", "params": {"text": "노트 내용"}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("노트에 기록해줘")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "write_note"
            assert result.actions[0].agent == "NoteAgent"
    
    @pytest.mark.asyncio
    async def test_parse_korean_record_keyword(self, parser, mock_openai_response):
        """Test parsing Korean '기록' keyword to NoteAgent"""
        response_json = '{"actions": [{"intent": "write_note", "agent": "NoteAgent", "params": {"text": "기록 내용"}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("기록 남겨줘")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "write_note"
            assert result.actions[0].agent == "NoteAgent"
    
    @pytest.mark.asyncio
    async def test_parse_calendar_list_request(self, parser, mock_openai_response):
        """Test parsing calendar list request"""
        response_json = '{"actions": [{"intent": "calendar_list", "agent": "CalendarAgent", "params": {}}]}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("이번주 일정 알려줘")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "calendar_list"
            assert result.actions[0].agent == "CalendarAgent"
    
    @pytest.mark.asyncio
    async def test_parse_invalid_json_fallback(self, parser, mock_openai_response):
        """Test fallback when JSON parsing fails"""
        # Return invalid JSON
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response("This is not valid JSON")
            
            result = await parser.parse_request("알 수 없는 요청")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "unknown"
            assert result.actions[0].agent == "FallbackAgent"
            assert result.raw_text == "알 수 없는 요청"
    
    @pytest.mark.asyncio
    async def test_parse_api_error_fallback(self, parser):
        """Test fallback when API call fails"""
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            result = await parser.parse_request("테스트 요청")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "unknown"
            assert result.actions[0].agent == "FallbackAgent"
            assert "error" in result.actions[0].params


    @pytest.mark.asyncio
    async def test_parse_multi_action_request(self, parser, mock_openai_response):
        """Test parsing multi-action request with dependencies"""
        response_json = '''{"actions": [
            {"intent": "unknown", "agent": "FallbackAgent", "params": {"text": "안녕"}, "use_results_from": []},
            {"intent": "web_search", "agent": "WebAgent", "params": {"query": "부산역 주변 맛집"}, "use_results_from": []},
            {"intent": "calendar_add", "agent": "CalendarAgent", "params": {"text": "내일 3시에 밥약속"}, "use_results_from": [2]}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("안녕, 내일 3시에 밥을 먹을거라 부산역 주변 맛집 찾아서 일정 만들어")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 3
            assert result.actions[0].intent == "unknown"
            assert result.actions[0].agent == "FallbackAgent"
            assert result.actions[0].use_results_from == []
            assert result.actions[1].intent == "web_search"
            assert result.actions[1].agent == "WebAgent"
            assert result.actions[1].use_results_from == []
            assert result.actions[2].intent == "calendar_add"
            assert result.actions[2].agent == "CalendarAgent"
            assert result.actions[2].use_results_from == [2]
    
    @pytest.mark.asyncio
    async def test_parse_empty_actions_fallback(self, parser, mock_openai_response):
        """Test fallback when actions array is empty"""
        response_json = '{"actions": []}'
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("알 수 없는 요청")
            
            assert len(result.actions) == 1
            assert result.actions[0].intent == "unknown"
            assert result.actions[0].agent == "FallbackAgent"
    
    @pytest.mark.asyncio
    async def test_parse_search_and_note_request(self, parser, mock_openai_response):
        """Test parsing request that needs web search before creating note"""
        response_json = '''{"actions": [
            {"intent": "web_search", "agent": "WebAgent", "params": {"query": "테슬라 최근 근황"}, "use_results_from": []},
            {"intent": "write_note", "agent": "NoteAgent", "params": {"text": "테슬라 최근 근황"}, "use_results_from": [1]}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("테슬라 최근 근황 정리,요약해서 메모 남겨줘")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 2
            assert result.actions[0].intent == "web_search"
            assert result.actions[0].agent == "WebAgent"
            assert result.actions[0].params["query"] == "테슬라 최근 근황"
            assert result.actions[0].use_results_from == []
            assert result.actions[1].intent == "write_note"
            assert result.actions[1].agent == "NoteAgent"
            assert result.actions[1].use_results_from == [1]
    
    @pytest.mark.asyncio
    async def test_parse_us_stock_market_note_request(self, parser, mock_openai_response):
        """Test parsing US stock market info request with note"""
        response_json = '''{"actions": [
            {"intent": "web_search", "agent": "WebAgent", "params": {"query": "미 증시 현황"}, "use_results_from": []},
            {"intent": "write_note", "agent": "NoteAgent", "params": {"text": "미 증시 현황"}, "use_results_from": [1]}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("미 증시 현황 요약해서 노트에 저장")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 2
            assert result.actions[0].intent == "web_search"
            assert result.actions[0].agent == "WebAgent"
            assert result.actions[1].intent == "write_note"
            assert result.actions[1].agent == "NoteAgent"
            assert result.actions[1].use_results_from == [1]
    
    @pytest.mark.asyncio
    async def test_parse_python_news_search_and_note(self, parser, mock_openai_response):
        """Test parsing Python news search with note creation"""
        response_json = '''{"actions": [
            {"intent": "web_search", "agent": "WebAgent", "params": {"query": "파이썬 최신 뉴스"}, "use_results_from": []},
            {"intent": "write_note", "agent": "NoteAgent", "params": {"text": "파이썬 최신 뉴스"}, "use_results_from": [1]}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("파이썬 최신 뉴스 검색하고 메모해줘")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 2
            assert result.actions[0].intent == "web_search"
            assert result.actions[1].intent == "write_note"
            assert result.actions[1].use_results_from == [1]
    
    @pytest.mark.asyncio
    async def test_parse_external_info_apple_stock(self, parser, mock_openai_response):
        """Test parsing external info request - Apple stock without explicit keywords"""
        response_json = '''{"actions": [
            {"intent": "web_search", "agent": "WebAgent", "params": {"query": "애플 주가"}, "use_results_from": []},
            {"intent": "write_note", "agent": "NoteAgent", "params": {"text": "애플 주가"}, "use_results_from": [1]}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("애플 주가 메모해줘")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 2
            assert result.actions[0].intent == "web_search"
            assert result.actions[0].agent == "WebAgent"
            assert result.actions[1].intent == "write_note"
            assert result.actions[1].use_results_from == [1]
    
    @pytest.mark.asyncio
    async def test_parse_external_info_samsung_earnings(self, parser, mock_openai_response):
        """Test parsing external info request - Samsung earnings"""
        response_json = '''{"actions": [
            {"intent": "web_search", "agent": "WebAgent", "params": {"query": "삼성전자 실적"}, "use_results_from": []},
            {"intent": "write_note", "agent": "NoteAgent", "params": {"text": "삼성전자 실적"}, "use_results_from": [1]}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("삼성전자 실적 노트에 저장")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 2
            assert result.actions[0].intent == "web_search"
            assert result.actions[1].intent == "write_note"
            assert result.actions[1].use_results_from == [1]
    
    @pytest.mark.asyncio
    async def test_parse_external_info_bitcoin_price(self, parser, mock_openai_response):
        """Test parsing external info request - Bitcoin price"""
        response_json = '''{"actions": [
            {"intent": "web_search", "agent": "WebAgent", "params": {"query": "비트코인 시세"}, "use_results_from": []},
            {"intent": "write_note", "agent": "NoteAgent", "params": {"text": "비트코인 시세"}, "use_results_from": [1]}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("비트코인 시세 기록")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 2
            assert result.actions[0].intent == "web_search"
            assert result.actions[1].intent == "write_note"
            assert result.actions[1].use_results_from == [1]
    
    @pytest.mark.asyncio
    async def test_parse_internal_info_personal_note(self, parser, mock_openai_response):
        """Test parsing internal info - personal note without search"""
        response_json = '''{"actions": [
            {"intent": "write_note", "agent": "NoteAgent", "params": {"text": "오늘 한 일 기록해줘"}, "use_results_from": []}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("오늘 한 일 기록해줘")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 1
            assert result.actions[0].intent == "write_note"
            assert result.actions[0].agent == "NoteAgent"
            assert result.actions[0].use_results_from == []
    
    @pytest.mark.asyncio
    async def test_parse_internal_info_personal_schedule(self, parser, mock_openai_response):
        """Test parsing internal info - personal schedule without search"""
        response_json = '''{"actions": [
            {"intent": "calendar_add", "agent": "CalendarAgent", "params": {"text": "내일 3시 회의"}, "use_results_from": []}
        ]}'''
        
        with patch.object(parser.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response(response_json)
            
            result = await parser.parse_request("내일 3시 회의 일정 추가")
            
            assert isinstance(result, ParsedRequest)
            assert len(result.actions) == 1
            assert result.actions[0].intent == "calendar_add"
            assert result.actions[0].agent == "CalendarAgent"
            assert result.actions[0].use_results_from == []


class TestParsedRequestSchema:
    """Test ParsedRequest Pydantic model"""
    
    def test_parsed_request_creation(self):
        """Test creating ParsedRequest with valid data"""
        action = AgentAction(
            intent="write_note",
            agent="NoteAgent",
            params={"text": "테스트"}
        )
        request = ParsedRequest(
            actions=[action],
            raw_text="메모 작성해줘"
        )
        
        assert len(request.actions) == 1
        assert request.actions[0].intent == "write_note"
        assert request.actions[0].agent == "NoteAgent"
        assert request.raw_text == "메모 작성해줘"
    
    def test_parsed_request_default_actions(self):
        """Test ParsedRequest with default empty actions"""
        request = ParsedRequest(
            raw_text="테스트"
        )
        
        assert request.actions == []
        assert request.raw_text == "테스트"
    
    def test_parsed_request_multiple_actions(self):
        """Test ParsedRequest with multiple actions"""
        actions = [
            AgentAction(intent="unknown", agent="FallbackAgent", params={}),
            AgentAction(intent="web_search", agent="WebAgent", params={"query": "test"}),
            AgentAction(intent="calendar_add", agent="CalendarAgent", params={"text": "meeting"})
        ]
        request = ParsedRequest(
            actions=actions,
            raw_text="복합 요청"
        )
        
        assert len(request.actions) == 3
        assert request.actions[0].intent == "unknown"
        assert request.actions[1].intent == "web_search"
        assert request.actions[2].intent == "calendar_add"
