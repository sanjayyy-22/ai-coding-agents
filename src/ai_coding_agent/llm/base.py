"""Base classes for LLM providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncIterator, Union
from pydantic import BaseModel
import tiktoken


class Message(BaseModel):
    """Represents a conversation message."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class LLMResponse(BaseModel):
    """Represents a response from an LLM."""
    content: str
    finish_reason: str
    usage: Dict[str, int]
    model: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "default", **kwargs):
        self.api_key = api_key
        self.model = model
        self.kwargs = kwargs
        self._client = None
        self._tokenizer = None
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (async setup)."""
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def stream_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a response from the LLM."""
        pass
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._tokenizer is None:
            try:
                self._tokenizer = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fallback to a general tokenizer
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
        
        return len(self._tokenizer.encode(text))
    
    def truncate_context(
        self, 
        messages: List[Message], 
        max_tokens: int, 
        preserve_system: bool = True
    ) -> List[Message]:
        """Truncate messages to fit within token limit."""
        if not messages:
            return messages
        
        # Always preserve system message if requested
        system_messages = []
        other_messages = []
        
        for msg in messages:
            if msg.role == "system" and preserve_system:
                system_messages.append(msg)
            else:
                other_messages.append(msg)
        
        # Count tokens for system messages
        system_tokens = sum(self.count_tokens(msg.content) for msg in system_messages)
        available_tokens = max_tokens - system_tokens
        
        if available_tokens <= 0:
            return system_messages
        
        # Add messages from the end until we hit the limit
        current_tokens = 0
        truncated_messages = []
        
        for msg in reversed(other_messages):
            msg_tokens = self.count_tokens(msg.content)
            if current_tokens + msg_tokens <= available_tokens:
                truncated_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        return system_messages + truncated_messages
    
    @property
    def name(self) -> str:
        """Get provider name."""
        return self.__class__.__name__.replace("Provider", "").lower()
    
    @property
    def is_available(self) -> bool:
        """Check if provider is available."""
        return self.api_key is not None
    
    def format_messages_for_api(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format messages for API calls."""
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.name:
                formatted_msg["name"] = msg.name
            if msg.tool_calls:
                formatted_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                formatted_msg["tool_call_id"] = msg.tool_call_id
            formatted.append(formatted_msg)
        return formatted