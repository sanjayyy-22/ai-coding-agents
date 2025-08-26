"""LLM Manager for coordinating multiple providers."""

import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator, Type
from .base import BaseLLMProvider, Message, LLMResponse
from .providers import OpenAIProvider, AnthropicProvider, LocalProvider
from ..utils.config import config_manager


class LLMManager:
    """Manages multiple LLM providers and handles fallbacks."""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.primary_provider: Optional[str] = None
        self.fallback_providers: List[str] = []
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize available providers based on configuration."""
        if self._initialized:
            return
        
        config = config_manager.config
        
        # Register available providers
        provider_classes: Dict[str, Type[BaseLLMProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "local": LocalProvider
        }
        
        # Initialize primary provider
        primary_provider = config.llm.provider
        if primary_provider in provider_classes:
            try:
                provider_class = provider_classes[primary_provider]
                
                if primary_provider == "openai":
                    provider = provider_class(
                        api_key=config.llm.api_key,
                        model=config.llm.model or "gpt-4"
                    )
                elif primary_provider == "anthropic":
                    provider = provider_class(
                        api_key=config.llm.api_key,
                        model=config.llm.model or "claude-3-sonnet-20240229"
                    )
                elif primary_provider == "local":
                    provider = provider_class(
                        model=config.llm.model or "llama2",
                        base_url=config.llm.base_url or "http://localhost:11434"
                    )
                
                await provider.initialize()
                self.providers[primary_provider] = provider
                self.primary_provider = primary_provider
            except Exception as e:
                print(f"Warning: Failed to initialize {primary_provider}: {e}")
        
        # Initialize fallback providers (if primary fails)
        fallback_order = ["openai", "anthropic", "local"]
        for provider_name in fallback_order:
            if provider_name != self.primary_provider and provider_name not in self.providers:
                try:
                    provider_class = provider_classes[provider_name]
                    
                    # Try to initialize with available credentials
                    if provider_name == "openai" and config.llm.api_key and config.llm.provider == "openai":
                        continue  # Already handled as primary
                    elif provider_name == "anthropic" and config.llm.api_key and config.llm.provider == "anthropic":
                        continue  # Already handled as primary
                    elif provider_name == "local":
                        # Local provider doesn't need API key
                        provider = LocalProvider(
                            model="llama2",
                            base_url="http://localhost:11434"
                        )
                        await provider.initialize()
                        self.providers[provider_name] = provider
                        self.fallback_providers.append(provider_name)
                except Exception:
                    # Silently fail for fallback providers
                    pass
        
        self._initialized = True
        
        if not self.providers:
            raise Exception("No LLM providers available. Please configure at least one provider.")
    
    async def generate_response(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using the best available provider."""
        await self.initialize()
        
        # Try primary provider first
        if self.primary_provider and self.primary_provider in self.providers:
            try:
                return await self.providers[self.primary_provider].generate_response(
                    messages, tools, **kwargs
                )
            except Exception as e:
                print(f"Primary provider {self.primary_provider} failed: {e}")
        
        # Try fallback providers
        for provider_name in self.fallback_providers:
            if provider_name in self.providers:
                try:
                    return await self.providers[provider_name].generate_response(
                        messages, tools, **kwargs
                    )
                except Exception as e:
                    print(f"Fallback provider {provider_name} failed: {e}")
        
        raise Exception("All LLM providers failed")
    
    async def stream_response(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a response using the best available provider."""
        await self.initialize()
        
        # Try primary provider first
        if self.primary_provider and self.primary_provider in self.providers:
            try:
                async for chunk in self.providers[self.primary_provider].stream_response(
                    messages, tools, **kwargs
                ):
                    yield chunk
                return
            except Exception as e:
                print(f"Primary provider {self.primary_provider} streaming failed: {e}")
        
        # Try fallback providers
        for provider_name in self.fallback_providers:
            if provider_name in self.providers:
                try:
                    async for chunk in self.providers[provider_name].stream_response(
                        messages, tools, **kwargs
                    ):
                        yield chunk
                    return
                except Exception as e:
                    print(f"Fallback provider {provider_name} streaming failed: {e}")
        
        raise Exception("All LLM providers failed for streaming")
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about available providers."""
        return {
            "primary": self.primary_provider,
            "fallbacks": self.fallback_providers,
            "available": list(self.providers.keys()),
            "total_providers": len(self.providers)
        }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using the primary provider."""
        if self.primary_provider and self.primary_provider in self.providers:
            return self.providers[self.primary_provider].count_tokens(text)
        elif self.providers:
            # Use any available provider for token counting
            return next(iter(self.providers.values())).count_tokens(text)
        else:
            # Fallback estimation (rough)
            return len(text.split()) * 1.3
    
    def truncate_context(
        self,
        messages: List[Message],
        max_tokens: int,
        preserve_system: bool = True
    ) -> List[Message]:
        """Truncate context using the primary provider."""
        if self.primary_provider and self.primary_provider in self.providers:
            return self.providers[self.primary_provider].truncate_context(
                messages, max_tokens, preserve_system
            )
        elif self.providers:
            # Use any available provider for truncation
            return next(iter(self.providers.values())).truncate_context(
                messages, max_tokens, preserve_system
            )
        else:
            # Simple fallback truncation
            if preserve_system:
                system_msgs = [m for m in messages if m.role == "system"]
                other_msgs = [m for m in messages if m.role != "system"]
                # Keep last few messages
                return system_msgs + other_msgs[-5:]
            else:
                return messages[-5:]


# Global LLM manager instance
llm_manager = LLMManager()