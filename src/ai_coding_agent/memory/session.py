"""Session memory for current conversation context."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
from .base import BaseMemory, MemoryEntry, MemoryType, MemoryStats


class SessionMemory(BaseMemory):
    """In-memory storage for current session context."""
    
    def __init__(self, max_entries: int = 1000, max_context_entries: int = 50):
        super().__init__(max_entries)
        self.max_context_entries = max_context_entries
        self.entries: Dict[str, MemoryEntry] = {}
        self.recent_entries: deque = deque(maxlen=max_entries)
        self.context_entries: deque = deque(maxlen=max_context_entries)
        self._lock = asyncio.Lock()
    
    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry in session."""
        async with self._lock:
            # Add to main storage
            self.entries[entry.id] = entry
            self.recent_entries.append(entry.id)
            
            # Add to context if it's conversation or important
            if (entry.type == MemoryType.CONVERSATION or 
                entry.importance > 0.7 or
                entry.type in [MemoryType.ERROR, MemoryType.SUCCESS, MemoryType.USER_PREFERENCE]):
                self.context_entries.append(entry.id)
            
            # Clean up if we exceed max entries
            if len(self.entries) > self.max_entries:
                await self._cleanup_old_entries()
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """Retrieve memory entries based on query."""
        async with self._lock:
            matches = []
            query_lower = query.lower()
            
            for entry in self.entries.values():
                # Filter by type if specified
                if memory_type and entry.type != memory_type:
                    continue
                
                # Filter by tags if specified
                if tags and not any(tag in entry.tags for tag in tags):
                    continue
                
                # Check if query matches content or metadata
                if (query_lower in entry.content.lower() or
                    any(query_lower in str(v).lower() for v in entry.metadata.values()) or
                    any(query_lower in tag.lower() for tag in entry.tags)):
                    matches.append(entry)
            
            # Sort by importance and recency
            matches.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
            return matches[:limit]
    
    async def get_recent(
        self, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemoryEntry]:
        """Get recent memory entries."""
        async with self._lock:
            recent = []
            
            # Get entries in reverse chronological order
            for entry_id in reversed(self.recent_entries):
                if entry_id in self.entries:
                    entry = self.entries[entry_id]
                    
                    # Filter by type if specified
                    if memory_type and entry.type != memory_type:
                        continue
                    
                    recent.append(entry)
                    
                    if len(recent) >= limit:
                        break
            
            return recent
    
    async def get_context(self, limit: int = 20) -> List[MemoryEntry]:
        """Get context entries for conversation."""
        async with self._lock:
            context = []
            
            for entry_id in reversed(self.context_entries):
                if entry_id in self.entries:
                    context.append(self.entries[entry_id])
                    
                    if len(context) >= limit:
                        break
            
            return context
    
    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        async with self._lock:
            if entry_id not in self.entries:
                return False
            
            entry = self.entries[entry_id]
            
            # Update allowed fields
            if 'content' in updates:
                entry.content = updates['content']
            if 'metadata' in updates:
                entry.metadata.update(updates['metadata'])
            if 'importance' in updates:
                entry.importance = max(0.0, min(1.0, updates['importance']))
            if 'tags' in updates:
                entry.tags = updates['tags']
            
            return True
    
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        async with self._lock:
            if entry_id not in self.entries:
                return False
            
            del self.entries[entry_id]
            
            # Remove from recent entries
            try:
                while entry_id in self.recent_entries:
                    self.recent_entries.remove(entry_id)
            except ValueError:
                pass
            
            # Remove from context entries
            try:
                while entry_id in self.context_entries:
                    self.context_entries.remove(entry_id)
            except ValueError:
                pass
            
            return True
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """Clear memory entries."""
        async with self._lock:
            if memory_type is None:
                # Clear everything
                self.entries.clear()
                self.recent_entries.clear()
                self.context_entries.clear()
            else:
                # Clear specific type
                to_delete = [
                    entry_id for entry_id, entry in self.entries.items()
                    if entry.type == memory_type
                ]
                
                for entry_id in to_delete:
                    await self.delete(entry_id)
    
    async def count(self) -> int:
        """Get total number of memory entries."""
        return len(self.entries)
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        async with self._lock:
            now = datetime.now()
            expired_ids = []
            
            for entry_id, entry in self.entries.items():
                if entry.expires_at and entry.expires_at <= now:
                    expired_ids.append(entry_id)
            
            for entry_id in expired_ids:
                await self.delete(entry_id)
            
            return len(expired_ids)
    
    async def _cleanup_old_entries(self) -> None:
        """Clean up old entries when max_entries is exceeded."""
        # Calculate how many entries to remove
        entries_to_remove = len(self.entries) - self.max_entries + 100  # Remove extra to avoid frequent cleanup
        
        if entries_to_remove <= 0:
            return
        
        # Get entries sorted by importance (ascending) and age (oldest first)
        entries_by_priority = sorted(
            self.entries.items(),
            key=lambda x: (x[1].importance, x[1].timestamp)
        )
        
        # Remove the least important and oldest entries
        for i in range(min(entries_to_remove, len(entries_by_priority))):
            entry_id = entries_by_priority[i][0]
            await self.delete(entry_id)
    
    async def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        async with self._lock:
            if not self.entries:
                return MemoryStats()
            
            entries_by_type = {}
            total_importance = 0
            timestamps = []
            
            for entry in self.entries.values():
                entries_by_type[entry.type] = entries_by_type.get(entry.type, 0) + 1
                total_importance += entry.importance
                timestamps.append(entry.timestamp)
            
            return MemoryStats(
                total_entries=len(self.entries),
                entries_by_type=entries_by_type,
                memory_usage_mb=self._estimate_memory_usage(),
                oldest_entry=min(timestamps) if timestamps else None,
                newest_entry=max(timestamps) if timestamps else None,
                avg_importance=total_importance / len(self.entries) if self.entries else 0.0
            )
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        import sys
        
        total_bytes = 0
        
        for entry in self.entries.values():
            # Estimate size of entry
            total_bytes += sys.getsizeof(entry.content)
            total_bytes += sys.getsizeof(entry.metadata)
            total_bytes += sys.getsizeof(entry.tags)
            total_bytes += 200  # Base overhead
        
        return total_bytes / (1024 * 1024)  # Convert to MB
    
    async def add_conversation_turn(
        self, 
        user_message: str, 
        assistant_response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a conversation turn to memory."""
        base_metadata = metadata or {}
        
        # Store user message
        user_entry = self.create_entry(
            content=user_message,
            memory_type=MemoryType.CONVERSATION,
            metadata={**base_metadata, "role": "user"},
            importance=0.5,
            tags=["conversation", "user"]
        )
        await self.store(user_entry)
        
        # Store assistant response
        assistant_metadata = {**base_metadata, "role": "assistant"}
        if tool_calls:
            assistant_metadata["tool_calls"] = tool_calls
        
        assistant_entry = self.create_entry(
            content=assistant_response,
            memory_type=MemoryType.CONVERSATION,
            metadata=assistant_metadata,
            importance=0.5,
            tags=["conversation", "assistant"]
        )
        await self.store(assistant_entry)
    
    async def add_tool_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool = True
    ) -> None:
        """Add tool execution result to memory."""
        importance = self.calculate_importance(
            MemoryType.TOOL_RESULT,
            recency=1.0,
            frequency=1.0,
            success=success
        )
        
        content = f"Tool: {tool_name}\nResult: {result.get('content', '')}"
        
        entry = self.create_entry(
            content=content,
            memory_type=MemoryType.TOOL_RESULT,
            metadata={
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "success": success
            },
            importance=importance,
            tags=["tool", tool_name, "success" if success else "error"]
        )
        
        await self.store(entry)
    
    async def add_error(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ) -> None:
        """Add error information to memory."""
        entry = self.create_entry(
            content=error_message,
            memory_type=MemoryType.ERROR,
            metadata={
                "context": context or {},
                "recovery_suggestions": recovery_suggestions or []
            },
            importance=0.8,
            tags=["error", "failure"]
        )
        
        await self.store(entry)
    
    async def add_success(
        self,
        success_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add success information to memory."""
        entry = self.create_entry(
            content=success_message,
            memory_type=MemoryType.SUCCESS,
            metadata={"context": context or {}},
            importance=0.6,
            tags=["success", "achievement"]
        )
        
        await self.store(entry)