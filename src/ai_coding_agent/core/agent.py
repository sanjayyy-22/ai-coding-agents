"""Core AI Coding Agent implementing Perceive-Reason-Act-Learn loop."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncIterator
from ..llm.manager import llm_manager
from ..llm.base import Message, MemoryType
from ..memory.manager import memory_manager
from ..tools.base import tool_registry
from ..tools.filesystem import FileSystemTool
from ..tools.git import GitTool
from ..tools.code import CodeAnalysisTool
from ..tools.execution import ExecutionTool
from ..interface.terminal import _approval_callback
from ..utils.config import config_manager
from pathlib import Path


class AICodeAgent:
    """
    Core AI Coding Agent implementing the Perceive-Reason-Act-Learn loop.
    
    This agent serves as an intelligent pair-programming partner that can:
    - Understand context from conversations and codebase
    - Reason about problems using LLM capabilities
    - Act through safe tool execution
    - Learn from interactions and outcomes
    """
    
    def __init__(self):
        self.llm_manager = llm_manager
        self.memory_manager = memory_manager
        self.tool_registry = tool_registry
        self._initialized = False
        self.system_prompt = self._create_system_prompt()
    
    async def initialize(self) -> None:
        """Initialize the agent and all its components."""
        if self._initialized:
            return
        
        # Initialize LLM manager
        await self.llm_manager.initialize()
        
        # Initialize memory manager
        await self.memory_manager.initialize()
        
        # Register tools
        self._register_tools()
        
        # Set approval callback
        self.tool_registry.set_approval_callback(_approval_callback)
        
        self._initialized = True
    
    def _register_tools(self) -> None:
        """Register all available tools."""
        # Core development tools
        self.tool_registry.register(FileSystemTool())
        self.tool_registry.register(GitTool())
        self.tool_registry.register(CodeAnalysisTool())
        self.tool_registry.register(ExecutionTool())
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the agent."""
        return """You are an AI Coding Agent, an intelligent pair-programming partner designed to help developers with coding tasks. You implement a Perceive-Reason-Act-Learn loop:

🔍 PERCEIVE: Understand the user's request, current context, and available information
🧠 REASON: Analyze the situation and plan the best approach
⚡ ACT: Execute tools safely to accomplish tasks
📚 LEARN: Remember outcomes and improve future responses

## Core Capabilities

### Development Tools
- **Filesystem**: Read, write, search files and directories
- **Git**: Version control operations (status, diff, commit, branch management)
- **Code Analysis**: Linting, dependency analysis, complexity analysis, security scans
- **Execution**: Run commands, tests, builds with safety controls

### Safety & Approval
- All destructive operations require user approval
- Preview changes before applying them
- Provide clear explanations of actions
- Suggest recovery options when things go wrong

### Memory & Learning
- Remember conversation context and user preferences
- Learn from successful and failed interactions
- Build patterns for better future assistance
- Maintain project-specific knowledge

## Interaction Guidelines

1. **Be Conversational**: Communicate naturally while being helpful and informative
2. **Be Safe**: Always explain potentially dangerous operations and get approval
3. **Be Contextual**: Use memory and available information to provide relevant help
4. **Be Learning**: Adapt based on user feedback and interaction outcomes
5. **Be Efficient**: Use tools effectively to accomplish tasks quickly

## Tool Usage

When using tools:
- Explain what you're going to do before acting
- Show results clearly and explain their significance
- Handle errors gracefully with helpful suggestions
- Learn from outcomes to improve future tool usage

## Response Format

- Provide clear, helpful responses
- Use natural language, not technical jargon unless appropriate
- Structure information clearly when presenting complex data
- Always be ready to explain your reasoning

Remember: You're a helpful pair-programming partner. Your goal is to make development easier, safer, and more productive while helping users learn and improve their skills."""
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process a user message through the Perceive-Reason-Act-Learn loop.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Dictionary containing the response, tool calls, and metadata
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # PERCEIVE: Gather context and understand the request
            context = await self._perceive(user_message)
            
            # REASON: Generate response and plan actions
            response = await self._reason(context)
            
            # ACT: Execute any tool calls
            if response.tool_calls:
                tool_results = await self._act(response.tool_calls)
                
                # Update response with tool results
                response = await self._integrate_tool_results(context, response, tool_results)
            
            # LEARN: Store interaction in memory
            await self._learn(user_message, response, context)
            
            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "context_used": len(context["messages"]),
                    "tools_executed": len(response.tool_calls) if response.tool_calls else 0
                }
            }
        
        except Exception as e:
            # Handle errors gracefully
            error_response = await self._handle_error(e, user_message)
            return error_response
    
    async def _perceive(self, user_message: str) -> Dict[str, Any]:
        """
        Perceive: Gather current state and context.
        
        This includes:
        - Recent conversation history
        - Relevant memories from past interactions
        - Current working directory and git status
        - Available tools and their capabilities
        """
        context = {
            "user_message": user_message,
            "messages": [],
            "memories": [],
            "environment": {},
            "tools": self.tool_registry.get_function_definitions()
        }
        
        # Get conversation context
        conversation_context = await self.memory_manager.get_context(limit=10)
        
        # Build message history
        messages = [Message(role="system", content=self.system_prompt)]
        
        # Add relevant memories
        if user_message:
            relevant_memories = await self.memory_manager.retrieve(
                user_message, limit=5, include_persistent=True
            )
            context["memories"] = relevant_memories
            
            # Add important memories to context
            for memory in relevant_memories:
                if memory.importance > 0.7:
                    messages.append(Message(
                        role="system",
                        content=f"Relevant memory: {memory.content}"
                    ))
        
        # Add conversation history
        for memory in conversation_context:
            if memory.type == MemoryType.CONVERSATION:
                role = memory.metadata.get("role", "user")
                messages.append(Message(role=role, content=memory.content))
        
        # Add current user message
        messages.append(Message(role="user", content=user_message))
        
        context["messages"] = messages
        
        # Get environment context (working directory, git status, etc.)
        try:
            import os
            context["environment"] = {
                "working_directory": os.getcwd(),
                "files_in_directory": len(list(Path(".").iterdir())) if Path(".").exists() else 0
            }
        except:
            pass
        
        return context
    
    async def _reason(self, context: Dict[str, Any]) -> Any:
        """
        Reason: Use LLM to analyze context and generate response.
        
        This involves:
        - Understanding the user's intent
        - Planning the best approach
        - Deciding which tools to use
        - Generating an appropriate response
        """
        messages = context["messages"]
        tools = context["tools"]
        
        # Truncate context if needed
        max_tokens = config_manager.config.max_context_length
        truncated_messages = self.llm_manager.truncate_context(
            messages, max_tokens, preserve_system=True
        )
        
        # Generate response
        response = await self.llm_manager.generate_response(
            truncated_messages,
            tools=tools if tools else None,
            temperature=config_manager.config.llm.temperature,
            max_tokens=config_manager.config.llm.max_tokens
        )
        
        return response
    
    async def _act(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Act: Execute tool calls safely.
        
        This involves:
        - Validating tool calls
        - Executing tools with safety checks
        - Collecting results and handling errors
        """
        tool_results = []
        
        for tool_call in tool_calls:
            try:
                # Extract tool information
                tool_name = tool_call["function"]["name"]
                
                # Parse arguments
                arguments = tool_call["function"]["arguments"]
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                
                # Execute tool
                result = await self.tool_registry.execute_tool(tool_name, **arguments)
                
                # Store result
                tool_results.append({
                    "tool_call_id": tool_call.get("id"),
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result.model_dump(),
                    "success": result.status.value == "success"
                })
                
                # Add to memory
                await self.memory_manager.add_tool_result(
                    tool_name, arguments, result.model_dump(), 
                    result.status.value == "success"
                )
            
            except Exception as e:
                # Handle tool execution errors
                error_result = {
                    "tool_call_id": tool_call.get("id"),
                    "tool_name": tool_call.get("function", {}).get("name", "unknown"),
                    "arguments": tool_call.get("function", {}).get("arguments", {}),
                    "result": {"error": str(e), "status": "error"},
                    "success": False
                }
                tool_results.append(error_result)
                
                # Add error to memory
                await self.memory_manager.add_error(
                    f"Tool execution failed: {e}",
                    {"tool_name": tool_call.get("function", {}).get("name", "unknown")}
                )
        
        return tool_results
    
    async def _integrate_tool_results(
        self, 
        context: Dict[str, Any], 
        response: Any, 
        tool_results: List[Dict[str, Any]]
    ) -> Any:
        """Integrate tool results into the response."""
        # Create messages with tool results
        messages = context["messages"].copy()
        
        # Add assistant response with tool calls
        messages.append(Message(
            role="assistant",
            content=response.content or "",
            tool_calls=response.tool_calls
        ))
        
        # Add tool results
        for tool_result in tool_results:
            messages.append(Message(
                role="tool",
                content=json.dumps(tool_result["result"]),
                tool_call_id=tool_result.get("tool_call_id"),
                name=tool_result["tool_name"]
            ))
        
        # Get final response
        final_response = await self.llm_manager.generate_response(
            messages,
            temperature=config_manager.config.llm.temperature
        )
        
        return final_response
    
    async def _learn(
        self, 
        user_message: str, 
        response: Any, 
        context: Dict[str, Any]
    ) -> None:
        """
        Learn: Store interaction outcomes in memory.
        
        This involves:
        - Recording the conversation turn
        - Noting successful/failed operations
        - Updating user preferences if applicable
        - Building patterns for future use
        """
        # Store conversation turn
        await self.memory_manager.add_conversation_turn(
            user_message,
            response.content,
            response.tool_calls,
            {"context_size": len(context["messages"])}
        )
        
        # Learn from tool results if any
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call["function"]["name"]
                
                # This would be enhanced based on actual success/failure
                await self.memory_manager.learn_from_interaction(
                    f"tool_usage_{tool_name}",
                    {"user_request": user_message},
                    {"response": response.content},
                    True,  # Assume success for now
                    None
                )
    
    async def _handle_error(self, error: Exception, user_message: str) -> Dict[str, Any]:
        """Handle errors gracefully."""
        error_message = f"I encountered an error while processing your request: {str(error)}"
        
        # Store error in memory
        await self.memory_manager.add_error(
            error_message,
            {"user_message": user_message, "error_type": type(error).__name__}
        )
        
        return {
            "content": error_message + "\n\nPlease try rephrasing your request or check the system status.",
            "tool_calls": None,
            "metadata": {
                "error": True,
                "error_type": type(error).__name__,
                "timestamp": datetime.now().isoformat()
            }
        }
    
    async def stream_response(self, user_message: str) -> AsyncIterator[str]:
        """Stream a response for real-time interaction."""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Perceive context
            context = await self._perceive(user_message)
            
            # Stream reasoning
            async for chunk in self.llm_manager.stream_response(
                context["messages"],
                tools=context["tools"]
            ):
                yield chunk
            
            # Note: Tool execution would happen after streaming completes
            # This is a simplified version for demonstration
        
        except Exception as e:
            yield f"Error: {str(e)}"