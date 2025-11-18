"""
HTTP Fetcher MCP Tool - Web requests
"""
import httpx
from typing import Dict, Any


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
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url)
            elif method.upper() == "POST":
                response = await client.post(url)
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
