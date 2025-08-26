"""Base classes for memory management."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    """Types of memory entries."""
    CONVERSATION = "conversation"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    SUCCESS = "success"
    CONTEXT = "context"
    LEARNING = "learning"
    USER_PREFERENCE = "user_preference"


class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: str
    type: MemoryType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    embeddings: Optional[List[float]] = None
    expires_at: Optional[datetime] = None


class BaseMemory(ABC):
    """Abstract base class for memory systems."""
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
    
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        pass
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None
    ) -> List[MemoryEntry]:
        """Retrieve memory entries based on query."""
        pass
    
    @abstractmethod
    async def get_recent(
        self, 
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemoryEntry]:
        """Get recent memory entries."""
        pass
    
    @abstractmethod
    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory entry."""
        pass
    
    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        pass
    
    @abstractmethod
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """Clear memory entries."""
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """Get total number of memory entries."""
        pass
    
    def create_entry(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None
    ) -> MemoryEntry:
        """Create a new memory entry."""
        import uuid
        
        return MemoryEntry(
            id=str(uuid.uuid4()),
            type=memory_type,
            content=content,
            metadata=metadata or {},
            importance=importance,
            tags=tags or [],
            expires_at=expires_at
        )
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        # Default implementation - can be overridden
        return 0
    
    def calculate_importance(
        self,
        memory_type: MemoryType,
        recency: float = 1.0,
        frequency: float = 1.0,
        success: bool = True
    ) -> float:
        """Calculate importance score for a memory entry."""
        # Base importance by type
        type_importance = {
            MemoryType.ERROR: 0.8,
            MemoryType.SUCCESS: 0.6,
            MemoryType.LEARNING: 0.9,
            MemoryType.USER_PREFERENCE: 0.95,
            MemoryType.TOOL_RESULT: 0.4,
            MemoryType.CONVERSATION: 0.3,
            MemoryType.CONTEXT: 0.5
        }
        
        base_score = type_importance.get(memory_type, 0.5)
        
        # Adjust based on factors
        importance = base_score * recency * frequency
        
        # Boost successful outcomes
        if success and memory_type in [MemoryType.TOOL_RESULT, MemoryType.SUCCESS]:
            importance *= 1.2
        
        # Normalize to [0, 1]
        return min(1.0, max(0.0, importance))


class MemoryQuery(BaseModel):
    """Query for memory retrieval."""
    text: str
    memory_types: Optional[List[MemoryType]] = None
    tags: Optional[List[str]] = None
    min_importance: Optional[float] = None
    max_age_hours: Optional[int] = None
    limit: int = 10
    semantic_search: bool = True


class MemoryStats(BaseModel):
    """Memory system statistics."""
    total_entries: int = 0
    entries_by_type: Dict[MemoryType, int] = Field(default_factory=dict)
    memory_usage_mb: float = 0.0
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None
    avg_importance: float = 0.0