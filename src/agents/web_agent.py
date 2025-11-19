"""
WebAgent - Handles web requests and search
"""
import sys
from pathlib import Path
from typing import Dict, Any
from openai import AsyncOpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base import AgentBase
from config import OPENAI_API_KEY, OPENAI_MODEL


class WebAgent(AgentBase):
    """Agent for web requests and search"""
    
    def __init__(self, mcp_client=None):
        """Initialize WebAgent with OpenAI client"""
        super().__init__(mcp_client)
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def _summarize_with_llm(self, query: str, contents: list) -> str:
        """
        Summarize search results using LLM
        
        Args:
            query: Original search query
            contents: List of dicts with 'title', 'url', 'text'
            
        Returns:
            Summarized text
        """
        # Build prompt with all content
        content_text = ""
        for i, content in enumerate(contents, 1):
            content_text += f"\n\n=== 결과 {i}: {content['title']} ===\n"
            content_text += f"URL: {content['url']}\n"
            content_text += f"내용: {content['text']}\n"
        
        prompt = f"""다음은 "{query}"에 대한 검색 결과입니다.

{content_text}

위 검색 결과들을 종합하여 사용자의 질문에 대한 답변을 작성해주세요.
- 핵심 정보를 요약하고 정리해주세요
- 여러 출처의 정보를 통합하여 일관된 답변을 제공해주세요
- 중요한 사실이나 수치가 있다면 포함해주세요
- 출처 URL을 참고 링크로 포함해주세요"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "당신은 검색 결과를 분석하고 요약하는 AI 어시스턴트입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"요약 생성 중 오류 발생: {str(e)}"
    
    async def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle web operation requests
        
        Supported operations:
        - web_search: Search and summarize top 3 results
        - fetch: Direct HTTP request
        
        Args:
            params: Dictionary with 'url' or 'query'
            
        Returns:
            Dictionary with status, result, and message
        """
        if self.mcp is None:
            return self._create_error_response("MCP client not available")
        
        # Get URL or query
        url = params.get("url")
        query = params.get("query")
        
        if not url and not query:
            return self._create_error_response("URL or query is required")
        
        try:
            # If query is provided, perform search and summarization
            if query:
                # Step 1: Search for top results
                search_result = await self.mcp.call("http_fetcher", "search", {"query": query, "max_results": 3})
                
                if search_result["status"] != "ok":
                    return search_result
                
                search_results = search_result["result"]
                
                # Step 2: Fetch content from each result
                contents = []
                for result in search_results:
                    fetch_result = await self.mcp.call(
                        "http_fetcher", 
                        "fetch_and_extract", 
                        {"url": result["url"], "max_length": 3000}
                    )
                    
                    if fetch_result["status"] == "ok":
                        contents.append({
                            "title": result["title"],
                            "url": result["url"],
                            "text": fetch_result["result"]["text"]
                        })
                
                if not contents:
                    return self._create_error_response("검색 결과를 가져올 수 없습니다")
                
                # Step 3: Summarize with LLM
                summary = await self._summarize_with_llm(query, contents)
                
                return {
                    "status": "ok",
                    "result": {
                        "query": query,
                        "summary": summary,
                        "sources": [{"title": c["title"], "url": c["url"]} for c in contents]
                    },
                    "message": f"검색 완료: {len(contents)}개 결과 요약"
                }
            
            # If URL is provided, just fetch it
            else:
                result = await self.mcp.call("http_fetcher", "fetch", {"url": url})
                return result
            
        except Exception as e:
            return self._create_error_response(
                message=f"Error handling web request",
                error=e
            )
