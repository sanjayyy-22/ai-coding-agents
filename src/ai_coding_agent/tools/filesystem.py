"""Filesystem operations tool."""

import os
import asyncio
import aiofiles
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from .base import BaseTool, ToolResult, ToolResultStatus
from ..utils.config import config_manager


class FileSystemTool(BaseTool):
    """Tool for filesystem operations."""
    
    def __init__(self):
        super().__init__()
        self.name = "filesystem"
    
    @property
    def description(self) -> str:
        return "Read, write, search, and manage files and directories"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "search", "list", "mkdir", "delete", "copy", "move", "exists"],
                    "description": "The filesystem operation to perform"
                },
                "path": {
                    "type": "string",
                    "description": "File or directory path"
                },
                "content": {
                    "type": "string",
                    "description": "Content for write operations"
                },
                "pattern": {
                    "type": "string",
                    "description": "Search pattern for search operations"
                },
                "recursive": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to operate recursively"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path for copy/move operations"
                }
            },
            "required": ["operation", "path"]
        }
    
    def is_safe_operation(self, **kwargs) -> bool:
        """Check if operation is safe."""
        operation = kwargs.get("operation", "")
        path = kwargs.get("path", "")
        
        # Write, delete, move operations require approval
        if operation in ["write", "delete", "move"]:
            return False
        
        # Operations outside current directory require approval  
        if os.path.isabs(path) and not path.startswith(os.getcwd()):
            return False
        
        # Large file operations require approval
        if operation == "write":
            content = kwargs.get("content", "")
            if len(content) > config_manager.config.max_file_size:
                return False
        
        return True
    
    def get_preview(self, **kwargs) -> str:
        """Get operation preview."""
        operation = kwargs.get("operation", "")
        path = kwargs.get("path", "")
        
        if operation == "read":
            return f"Read file: {path}"
        elif operation == "write":
            content_preview = kwargs.get("content", "")[:100]
            return f"Write to {path}: {content_preview}..."
        elif operation == "delete":
            return f"Delete: {path}"
        elif operation == "move":
            dest = kwargs.get("destination", "")
            return f"Move {path} to {dest}"
        elif operation == "copy":
            dest = kwargs.get("destination", "")
            return f"Copy {path} to {dest}"
        else:
            return f"Execute {operation} on {path}"
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute filesystem operation."""
        operation = kwargs.get("operation")
        path = kwargs.get("path")
        
        try:
            if operation == "read":
                return await self._read_file(path)
            elif operation == "write":
                content = kwargs.get("content", "")
                return await self._write_file(path, content)
            elif operation == "search":
                pattern = kwargs.get("pattern", "")
                recursive = kwargs.get("recursive", False)
                return await self._search_files(path, pattern, recursive)
            elif operation == "list":
                recursive = kwargs.get("recursive", False)
                return await self._list_directory(path, recursive)
            elif operation == "mkdir":
                return await self._make_directory(path)
            elif operation == "delete":
                return await self._delete_path(path)
            elif operation == "copy":
                destination = kwargs.get("destination", "")
                return await self._copy_path(path, destination)
            elif operation == "move":
                destination = kwargs.get("destination", "")
                return await self._move_path(path, destination)
            elif operation == "exists":
                return await self._check_exists(path)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"Unknown operation: {operation}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e),
                suggested_actions=[
                    "Check if path exists",
                    "Verify file permissions",
                    "Check disk space"
                ]
            )
    
    async def _read_file(self, path: str) -> ToolResult:
        """Read a file."""
        file_path = Path(path)
        
        if not file_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File not found: {path}"
            )
        
        if not file_path.is_file():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Path is not a file: {path}"
            )
        
        # Check file size
        if file_path.stat().st_size > config_manager.config.max_file_size:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File too large: {path} ({file_path.stat().st_size} bytes)"
            )
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=content,
                data={
                    "path": str(file_path.absolute()),
                    "size": file_path.stat().st_size,
                    "lines": len(content.splitlines())
                }
            )
        
        except UnicodeDecodeError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"File appears to be binary: {path}"
            )
    
    async def _write_file(self, path: str, content: str) -> ToolResult:
        """Write content to a file."""
        file_path = Path(path)
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing file if it exists
        backup_path = None
        if file_path.exists() and config_manager.config.auto_backup:
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            shutil.copy2(file_path, backup_path)
        
        try:
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            result_data = {
                "path": str(file_path.absolute()),
                "size": len(content),
                "lines": len(content.splitlines())
            }
            
            if backup_path:
                result_data["backup"] = str(backup_path)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Successfully wrote {len(content)} characters to {path}",
                data=result_data
            )
        
        except Exception as e:
            # Restore backup if write failed
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, file_path)
                backup_path.unlink()
            raise e
    
    async def _search_files(self, path: str, pattern: str, recursive: bool = False) -> ToolResult:
        """Search for files matching a pattern."""
        search_path = Path(path)
        
        if not search_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Path not found: {path}"
            )
        
        matches = []
        
        try:
            if search_path.is_file():
                # Search within file content
                async with aiofiles.open(search_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    lines = content.splitlines()
                    for i, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower():
                            matches.append({
                                "file": str(search_path),
                                "line": i,
                                "content": line.strip()
                            })
            else:
                # Search for files by name
                if recursive:
                    glob_pattern = f"**/*{pattern}*"
                else:
                    glob_pattern = f"*{pattern}*"
                
                for match in search_path.glob(glob_pattern):
                    matches.append({
                        "path": str(match),
                        "type": "directory" if match.is_dir() else "file",
                        "size": match.stat().st_size if match.is_file() else None
                    })
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Found {len(matches)} matches for '{pattern}' in {path}",
                data={
                    "matches": matches,
                    "pattern": pattern,
                    "search_path": str(search_path),
                    "recursive": recursive
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Search failed: {str(e)}"
            )
    
    async def _list_directory(self, path: str, recursive: bool = False) -> ToolResult:
        """List directory contents."""
        dir_path = Path(path)
        
        if not dir_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Directory not found: {path}"
            )
        
        if not dir_path.is_dir():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Path is not a directory: {path}"
            )
        
        entries = []
        
        try:
            if recursive:
                for item in dir_path.rglob("*"):
                    entries.append({
                        "path": str(item.relative_to(dir_path)),
                        "absolute_path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
            else:
                for item in dir_path.iterdir():
                    entries.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None
                    })
            
            # Sort entries
            entries.sort(key=lambda x: (x["type"] == "file", x.get("name", x.get("path", ""))))
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Listed {len(entries)} items in {path}",
                data={
                    "entries": entries,
                    "directory": str(dir_path),
                    "recursive": recursive
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to list directory: {str(e)}"
            )
    
    async def _make_directory(self, path: str) -> ToolResult:
        """Create a directory."""
        dir_path = Path(path)
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Created directory: {path}",
                data={"path": str(dir_path.absolute())}
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to create directory: {str(e)}"
            )
    
    async def _delete_path(self, path: str) -> ToolResult:
        """Delete a file or directory."""
        target_path = Path(path)
        
        if not target_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Path not found: {path}"
            )
        
        try:
            if target_path.is_file():
                target_path.unlink()
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    content=f"Deleted file: {path}"
                )
            else:
                shutil.rmtree(target_path)
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    content=f"Deleted directory: {path}"
                )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to delete: {str(e)}"
            )
    
    async def _copy_path(self, source: str, destination: str) -> ToolResult:
        """Copy a file or directory."""
        src_path = Path(source)
        dst_path = Path(destination)
        
        if not src_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Source not found: {source}"
            )
        
        try:
            if src_path.is_file():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            else:
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Copied {source} to {destination}",
                data={
                    "source": str(src_path.absolute()),
                    "destination": str(dst_path.absolute())
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to copy: {str(e)}"
            )
    
    async def _move_path(self, source: str, destination: str) -> ToolResult:
        """Move a file or directory."""
        src_path = Path(source)
        dst_path = Path(destination)
        
        if not src_path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Source not found: {source}"
            )
        
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                content=f"Moved {source} to {destination}",
                data={
                    "source": source,
                    "destination": str(dst_path.absolute())
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Failed to move: {str(e)}"
            )
    
    async def _check_exists(self, path: str) -> ToolResult:
        """Check if path exists."""
        target_path = Path(path)
        exists = target_path.exists()
        
        data = {
            "exists": exists,
            "path": str(target_path.absolute())
        }
        
        if exists:
            data.update({
                "is_file": target_path.is_file(),
                "is_directory": target_path.is_dir(),
                "size": target_path.stat().st_size if target_path.is_file() else None
            })
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content=f"Path {'exists' if exists else 'does not exist'}: {path}",
            data=data
        )