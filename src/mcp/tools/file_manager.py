"""
File Manager MCP Tool - File system operations
"""
import os
from pathlib import Path
from typing import Dict, Any, List


async def list_files(path: str = ".") -> Dict[str, Any]:
    """
    List files in a directory
    
    Args:
        path: Directory path to list
        
    Returns:
        Dictionary with status and file list
    """
    try:
        target_path = Path(path).expanduser()
        
        if not target_path.exists():
            return {
                "status": "error",
                "result": None,
                "message": f"Path does not exist: {path}"
            }
        
        if not target_path.is_dir():
            return {
                "status": "error",
                "result": None,
                "message": f"Path is not a directory: {path}"
            }
        
        # List files with metadata
        files = []
        for item in target_path.iterdir():
            try:
                stat = item.stat()
                files.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "path": str(item)
                })
            except Exception:
                # Skip files we can't access
                continue
        
        # Sort by name
        files.sort(key=lambda x: x["name"].lower())
        
        return {
            "status": "ok",
            "result": files,
            "message": f"Found {len(files)} items in {path}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error listing files: {str(e)}"
        }


async def read_file(path: str, max_bytes: int = 10000) -> Dict[str, Any]:
    """
    Read file contents
    
    Args:
        path: File path to read
        max_bytes: Maximum bytes to read (default 10KB)
        
    Returns:
        Dictionary with status and file content
    """
    try:
        target_path = Path(path).expanduser()
        
        if not target_path.exists():
            return {
                "status": "error",
                "result": None,
                "message": f"File does not exist: {path}"
            }
        
        if not target_path.is_file():
            return {
                "status": "error",
                "result": None,
                "message": f"Path is not a file: {path}"
            }
        
        # Check file size
        file_size = target_path.stat().st_size
        
        if file_size > max_bytes:
            # Read only first max_bytes
            with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_bytes)
            
            return {
                "status": "ok",
                "result": {
                    "content": content,
                    "truncated": True,
                    "size": file_size,
                    "read_bytes": max_bytes
                },
                "message": f"File content (truncated to {max_bytes} bytes)"
            }
        else:
            # Read entire file
            with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return {
                "status": "ok",
                "result": {
                    "content": content,
                    "truncated": False,
                    "size": file_size
                },
                "message": f"File content ({file_size} bytes)"
            }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error reading file: {str(e)}"
        }
