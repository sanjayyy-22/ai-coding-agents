"""Concrete LLM provider implementations."""

import json
import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator
import openai
import anthropic
import requests
from .base import BaseLLMProvider, Message, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = None
    
    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
    
    async def generate_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using OpenAI."""
        if not self.client:
            await self.initialize()
        
        formatted_messages = self.format_messages_for_api(messages)
        
        request_params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"
        
        try:
            response = await self.client.chat.completions.create(**request_params)
            
            choice = response.choices[0]
            content = choice.message.content or ""
            
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in choice.message.tool_calls
                ]
            
            return LLMResponse(
                content=content,
                finish_reason=choice.finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                model=response.model,
                tool_calls=tool_calls
            )
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def stream_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a response using OpenAI."""
        if not self.client:
            await self.initialize()
        
        formatted_messages = self.format_messages_for_api(messages)
        
        request_params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }
        
        if tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"
        
        try:
            stream = await self.client.chat.completions.create(**request_params)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {str(e)}")


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.client = None
    
    async def initialize(self) -> None:
        """Initialize the Anthropic client."""
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
    
    def _format_messages_for_anthropic(self, messages: List[Message]) -> tuple[str, List[Dict[str, str]]]:
        """Format messages for Anthropic API (separate system message)."""
        system_message = ""
        formatted_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_message += msg.content + "\n"
            elif msg.role in ["user", "assistant"]:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return system_message.strip(), formatted_messages
    
    async def generate_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using Anthropic."""
        if not self.client:
            await self.initialize()
        
        system_message, formatted_messages = self._format_messages_for_anthropic(messages)
        
        request_params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }
        
        if system_message:
            request_params["system"] = system_message
        
        if tools:
            # Convert tools to Anthropic format
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"]
                })
            request_params["tools"] = anthropic_tools
        
        try:
            response = await self.client.messages.create(**request_params)
            
            content = ""
            tool_calls = []
            
            for content_block in response.content:
                if content_block.type == "text":
                    content += content_block.text
                elif content_block.type == "tool_use":
                    tool_calls.append({
                        "id": content_block.id,
                        "type": "function",
                        "function": {
                            "name": content_block.name,
                            "arguments": json.dumps(content_block.input)
                        }
                    })
            
            return LLMResponse(
                content=content,
                finish_reason=response.stop_reason,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                model=response.model,
                tool_calls=tool_calls if tool_calls else None
            )
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    async def stream_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a response using Anthropic."""
        if not self.client:
            await self.initialize()
        
        system_message, formatted_messages = self._format_messages_for_anthropic(messages)
        
        request_params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }
        
        if system_message:
            request_params["system"] = system_message
        
        if tools:
            # Convert tools to Anthropic format
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "input_schema": tool["function"]["parameters"]
                })
            request_params["tools"] = anthropic_tools
        
        try:
            async with self.client.messages.stream(**request_params) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise Exception(f"Anthropic streaming error: {str(e)}")


class LocalProvider(BaseLLMProvider):
    """Local model provider (Ollama, OpenAI-compatible endpoints)."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama2", base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(api_key, model, **kwargs)
        self.base_url = base_url.rstrip('/')
    
    async def initialize(self) -> None:
        """Initialize the local provider."""
        # Test connection
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"Failed to connect to local model server: {str(e)}")
    
    async def generate_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using local model."""
        # Convert messages to a single prompt for Ollama
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.1),
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            return LLMResponse(
                content=result.get("response", ""),
                finish_reason="stop",
                usage={
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                },
                model=self.model,
                tool_calls=None  # Local models don't support tool calls yet
            )
        except Exception as e:
            raise Exception(f"Local model API error: {str(e)}")
    
    async def stream_response(
        self, 
        messages: List[Message], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a response using local model."""
        prompt = self._messages_to_prompt(messages)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.1),
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise Exception(f"Local model streaming error: {str(e)}")
    
    def _messages_to_prompt(self, messages: List[Message]) -> str:
        """Convert messages to a single prompt for local models."""
        prompt_parts = []
        
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"Human: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        prompt_parts.append("Assistant: ")
        return "\n\n".join(prompt_parts)