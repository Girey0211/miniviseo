"""
HTTP Fetcher MCP Tool - Web requests
"""
import httpx
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import re


def _extract_text_from_html(html: str) -> str:
    """
    Extract clean text from HTML content
    
    Args:
        html: HTML content
        
    Returns:
        Cleaned text content
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception:
        # If parsing fails, return original HTML
        return html


async def search(query: str, max_results: int = 3) -> Dict[str, Any]:
    """
    Search the web using DuckDuckGo and return top results
    
    Args:
        query: Search query
        max_results: Maximum number of results to return (default: 3)
        
    Returns:
        Dictionary with status and list of search results
    """
    try:
        # Use DuckDuckGo HTML search (no API key required)
        search_url = f"https://html.duckduckgo.com/html/?q={query}"
        
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = await client.get(search_url, headers=headers)
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Search failed with status {response.status_code}"
                }
            
            # Parse search results
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find result links
            for result_div in soup.find_all('div', class_='result')[:max_results]:
                title_elem = result_div.find('a', class_='result__a')
                snippet_elem = result_div.find('a', class_='result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    # Fix relative URLs from DuckDuckGo
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        url = 'https://duckduckgo.com' + url
                    
                    # Extract actual URL from DuckDuckGo redirect
                    if 'uddg=' in url:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.query)
                        if 'uddg' in params:
                            url = params['uddg'][0]
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
            
            if not results:
                return {
                    "status": "error",
                    "result": None,
                    "message": "No search results found"
                }
            
            return {
                "status": "ok",
                "result": results,
                "message": f"Found {len(results)} search results"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Search error: {str(e)}"
        }


async def fetch_and_extract(url: str, timeout: int = 10, max_length: int = 3000) -> Dict[str, Any]:
    """
    Fetch URL and extract clean text content
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_length: Maximum text length to return
        
    Returns:
        Dictionary with status and extracted text
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Failed to fetch {url} (status: {response.status_code})"
                }
            
            # Extract text from HTML
            text = _extract_text_from_html(response.text)
            
            # Limit text length
            truncated = len(text) > max_length
            text = text[:max_length]
            
            return {
                "status": "ok",
                "result": {
                    "url": url,
                    "text": text,
                    "truncated": truncated
                },
                "message": f"Extracted text from {url}"
            }
            
    except httpx.TimeoutException:
        return {
            "status": "error",
            "result": None,
            "message": f"Request timeout after {timeout} seconds"
        }
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error fetching URL: {str(e)}"
        }


async def fetch(url: str, method: str = "GET", timeout: int = 10) -> Dict[str, Any]:
    """
    Fetch content from a URL
    
    Args:
        url: URL to fetch
        method: HTTP method (default: GET)
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with status, response data
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers)
            else:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Unsupported HTTP method: {method}"
                }
            
            # Limit response text to reasonable size
            max_length = 5000
            text = response.text[:max_length]
            truncated = len(response.text) > max_length
            
            return {
                "status": "ok",
                "result": {
                    "url": url,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "text": text,
                    "truncated": truncated,
                    "length": len(response.text)
                },
                "message": f"Fetched {url} (status: {response.status_code})"
            }
            
    except httpx.TimeoutException:
        return {
            "status": "error",
            "result": None,
            "message": f"Request timeout after {timeout} seconds"
        }
    except httpx.RequestError as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Request error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error fetching URL: {str(e)}"
        }
