"""Memory manager that coordinates session and persistent memory."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .base import BaseMemory, MemoryEntry, MemoryType, MemoryStats
from .session import SessionMemory
from .persistent import PersistentMemory
from ..utils.config import config_manager


class MemoryManager:
    """Coordinates session and persistent memory systems."""
    
    def __init__(self):
        self.session_memory = SessionMemory()
        self.persistent_memory = PersistentMemory()
        self._initialized = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize both memory systems."""
        if self._initialized:
            return
        
        await self.persistent_memory.initialize()
        
        # Load recent persistent memories into session
        if config_manager.config.memory_persistence:
            await self._load_recent_memories()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        self._initialized = True
    
    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry in both session and persistent memory."""
        if not self._initialized:
            await self.initialize()
        
        # Always store in session memory
        await self.session_memory.store(entry)
        
        # Store in persistent memory if enabled and entry is important enough
        if (config_manager.config.memory_persistence and 
            (entry.importance >= 0.6 or 
             entry.type in [MemoryType.ERROR, MemoryType.SUCCESS, MemoryType.LEARNING, MemoryType.USER_PREFERENCE])):
            await self.persistent_memory.store(entry)
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        include_persistent: bool = True
    ) -> List[MemoryEntry]:
        """Retrieve memory entries from both session and persistent memory."""
        if not self._initialized:
            await self.initialize()
        
        # Get results from session memory
        session_results = await self.session_memory.retrieve(
            query, limit=limit//2, memory_type=memory_type, tags=tags
        )
        
        # Get results from persistent memory if enabled
        persistent_results = []
        if include_persistent and config_manager.config.memory_persistence:
            persistent_results = await self.persistent_memory.retrieve(
                query, limit=limit//2, memory_type=memory_type, tags=tags
            )
        
        # Combine and deduplicate results
        all_results = session_results + persistent_results
        seen_ids = set()
        unique_results = []
        
        for entry in all_results:
            if entry.id not in seen_ids:
                unique_results.append(entry)
                seen_ids.add(entry.id)
        
        # Sort by importance and recency
        unique_results.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
        
        return unique_results[:limit]
    
    async def get_recent(
        self, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        include_persistent: bool = False
    ) -> List[MemoryEntry]:
        """Get recent memory entries."""
        if not self._initialized:
            await self.initialize()
        
        # Primarily use session memory for recent entries
        session_results = await self.session_memory.get_recent(limit, memory_type)
        
        # Fill in with persistent memory if needed
        if include_persistent and len(session_results) < limit:
            remaining = limit - len(session_results)
            persistent_results = await self.persistent_memory.get_recent(remaining, memory_type)
            
            # Combine and deduplicate
            session_ids = {entry.id for entry in session_results}
            for entry in persistent_results:
                if entry.id not in session_ids:
                    session_results.append(entry)
                    if len(session_results) >= limit:
                        break
        
        return session_results[:limit]
    
    async def get_context(self, limit: int = 20) -> List[MemoryEntry]:
        """Get context entries for conversation."""
        if not self._initialized:
            await self.initialize()
        
        return await self.session_memory.get_context(limit)
    
    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry in both systems."""
        if not self._initialized:
            await self.initialize()
        
        session_updated = await self.session_memory.update(entry_id, updates)
        persistent_updated = await self.persistent_memory.update(entry_id, updates)
        
        return session_updated or persistent_updated
    
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry from both systems."""
        if not self._initialized:
            await self.initialize()
        
        session_deleted = await self.session_memory.delete(entry_id)
        persistent_deleted = await self.persistent_memory.delete(entry_id)
        
        return session_deleted or persistent_deleted
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """Clear memory entries from both systems."""
        if not self._initialized:
            await self.initialize()
        
        await self.session_memory.clear(memory_type)
        await self.persistent_memory.clear(memory_type)
    
    async def count(self) -> Dict[str, int]:
        """Get memory counts from both systems."""
        if not self._initialized:
            await self.initialize()
        
        session_count = await self.session_memory.count()
        persistent_count = await self.persistent_memory.count()
        
        return {
            "session": session_count,
            "persistent": persistent_count,
            "total": session_count + persistent_count
        }
    
    async def get_stats(self) -> Dict[str, MemoryStats]:
        """Get statistics from both memory systems."""
        if not self._initialized:
            await self.initialize()
        
        session_stats = await self.session_memory.get_stats()
        persistent_stats = await self.persistent_memory.get_stats()
        
        return {
            "session": session_stats,
            "persistent": persistent_stats
        }
    
    async def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired entries from both systems."""
        if not self._initialized:
            await self.initialize()
        
        session_cleaned = await self.session_memory.cleanup_expired()
        persistent_cleaned = await self.persistent_memory.cleanup_expired()
        
        return {
            "session": session_cleaned,
            "persistent": persistent_cleaned,
            "total": session_cleaned + persistent_cleaned
        }
    
    # Convenience methods for common operations
    
    async def add_conversation_turn(
        self, 
        user_message: str, 
        assistant_response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a conversation turn to memory."""
        await self.session_memory.add_conversation_turn(
            user_message, assistant_response, tool_calls, metadata
        )
    
    async def add_tool_result(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool = True
    ) -> None:
        """Add tool execution result to memory."""
        await self.session_memory.add_tool_result(tool_name, parameters, result, success)
        
        # Also store learning pattern in persistent memory
        if config_manager.config.memory_persistence:
            pattern_data = {
                "tool_name": tool_name,
                "parameters": parameters,
                "context": result.get("context", {})
            }
            await self.persistent_memory.store_learning_pattern(
                f"tool_{tool_name}", pattern_data, success
            )
    
    async def add_error(
        self,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ) -> None:
        """Add error information to memory."""
        await self.session_memory.add_error(error_message, context, recovery_suggestions)
        
        # Store error pattern in persistent memory for learning
        if config_manager.config.memory_persistence and context:
            pattern_data = {
                "error_type": context.get("error_type", "unknown"),
                "context": context,
                "recovery_suggestions": recovery_suggestions or []
            }
            await self.persistent_memory.store_learning_pattern(
                "error_pattern", pattern_data, False
            )
    
    async def add_success(
        self,
        success_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add success information to memory."""
        await self.session_memory.add_success(success_message, context)
        
        # Store success pattern in persistent memory
        if config_manager.config.memory_persistence and context:
            pattern_data = {
                "success_type": context.get("success_type", "general"),
                "context": context
            }
            await self.persistent_memory.store_learning_pattern(
                "success_pattern", pattern_data, True
            )
    
    async def learn_from_interaction(
        self,
        interaction_type: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        success: bool,
        user_feedback: Optional[str] = None
    ) -> None:
        """Learn from user interaction."""
        if not config_manager.config.memory_persistence:
            return
        
        # Create learning entry
        learning_content = f"Interaction: {interaction_type}\n"
        if user_feedback:
            learning_content += f"User feedback: {user_feedback}\n"
        learning_content += f"Success: {success}"
        
        entry = self.session_memory.create_entry(
            content=learning_content,
            memory_type=MemoryType.LEARNING,
            metadata={
                "interaction_type": interaction_type,
                "input_data": input_data,
                "output_data": output_data,
                "success": success,
                "user_feedback": user_feedback
            },
            importance=0.9,  # Learning entries are important
            tags=["learning", interaction_type, "success" if success else "failure"]
        )
        
        await self.store(entry)
        
        # Store pattern for future reference
        pattern_data = {
            "interaction_type": interaction_type,
            "input_context": input_data,
            "output_context": output_data,
            "feedback": user_feedback
        }
        
        await self.persistent_memory.store_learning_pattern(
            f"interaction_{interaction_type}", pattern_data, success
        )
    
    async def get_learning_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Get learning patterns from persistent memory."""
        if not config_manager.config.memory_persistence:
            return []
        
        return await self.persistent_memory.get_learning_patterns(
            pattern_type, min_confidence
        )
    
    async def store_user_preference(self, key: str, value: Any, category: str = "general") -> None:
        """Store a user preference."""
        if not config_manager.config.memory_persistence:
            return
        
        await self.persistent_memory.store_user_preference(key, value, category)
        
        # Also add to session memory for immediate access
        entry = self.session_memory.create_entry(
            content=f"User preference: {key} = {value}",
            memory_type=MemoryType.USER_PREFERENCE,
            metadata={"key": key, "value": value, "category": category},
            importance=0.95,  # User preferences are very important
            tags=["preference", category, key]
        )
        
        await self.session_memory.store(entry)
    
    async def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        if not config_manager.config.memory_persistence:
            return default
        
        return await self.persistent_memory.get_user_preference(key, default)
    
    async def get_user_preferences(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get all user preferences."""
        if not config_manager.config.memory_persistence:
            return {}
        
        return await self.persistent_memory.get_user_preferences(category)
    
    async def _load_recent_memories(self) -> None:
        """Load recent important memories from persistent storage into session."""
        # Load recent high-importance entries
        recent_important = await self.persistent_memory.retrieve(
            "", limit=50, memory_type=None, tags=None
        )
        
        # Filter and load into session
        for entry in recent_important:
            if (entry.importance >= 0.7 or 
                entry.type in [MemoryType.USER_PREFERENCE, MemoryType.LEARNING]):
                # Create a copy for session memory
                session_entry = MemoryEntry(
                    id=entry.id,
                    type=entry.type,
                    content=entry.content,
                    metadata=entry.metadata,
                    timestamp=entry.timestamp,
                    importance=entry.importance,
                    tags=entry.tags,
                    embeddings=entry.embeddings,
                    expires_at=entry.expires_at
                )
                await self.session_memory.store(session_entry)
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up expired entries
                await self.cleanup_expired()
                
                # Sync important session memories to persistent storage
                if config_manager.config.memory_persistence:
                    await self._sync_important_memories()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Memory cleanup error: {e}")
    
    async def _sync_important_memories(self) -> None:
        """Sync important session memories to persistent storage."""
        # Get high-importance session memories that might not be in persistent storage
        important_memories = await self.session_memory.retrieve(
            "", limit=100, memory_type=None, tags=None
        )
        
        for entry in important_memories:
            if (entry.importance >= 0.8 or 
                entry.type in [MemoryType.ERROR, MemoryType.SUCCESS, MemoryType.LEARNING]):
                await self.persistent_memory.store(entry)
    
    async def close(self) -> None:
        """Close memory systems."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self.persistent_memory.close()


# Global memory manager instance
memory_manager = MemoryManager()