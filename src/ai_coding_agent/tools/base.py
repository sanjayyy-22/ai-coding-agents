"""Base classes for tools in the AI Coding Agent."""

import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from pydantic import BaseModel, Field
from enum import Enum


class ToolResultStatus(str, Enum):
    """Status of tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    REQUIRES_APPROVAL = "requires_approval"
    CANCELLED = "cancelled"


class ToolResult(BaseModel):
    """Result of a tool execution."""
    status: ToolResultStatus
    content: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    requires_approval: bool = False
    suggested_actions: List[str] = Field(default_factory=list)


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    def __init__(self):
        self.name = self.__class__.__name__.replace("Tool", "").lower()
        self.requires_approval = False
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema for tool parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def to_function_definition(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def is_safe_operation(self, **kwargs) -> bool:
        """Check if operation is safe to execute without approval."""
        return True
    
    def get_preview(self, **kwargs) -> str:
        """Get a preview of what this tool will do."""
        return f"Will execute {self.name} with parameters: {kwargs}"
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and normalize parameters."""
        # Basic validation - can be overridden
        return kwargs
    
    async def safe_execute(self, **kwargs) -> ToolResult:
        """Execute tool with safety checks."""
        try:
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Check if approval is needed
            if not self.is_safe_operation(**validated_params):
                return ToolResult(
                    status=ToolResultStatus.REQUIRES_APPROVAL,
                    content=self.get_preview(**validated_params),
                    requires_approval=True
                )
            
            # Execute the tool
            return await self.execute(**validated_params)
            
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e),
                suggested_actions=[
                    "Check parameters and try again",
                    "Verify file paths and permissions",
                    "Check system requirements"
                ]
            )


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def unregister(self, tool_name: str) -> None:
        """Unregister a tool."""
        if tool_name in self._tools:
            del self._tools[tool_name]
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get function definitions for all tools."""
        return [tool.to_function_definition() for tool in self._tools.values()]
    
    def set_approval_callback(self, callback: Callable[[str, Dict[str, Any]], bool]) -> None:
        """Set callback for approval requests."""
        self._approval_callback = callback
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Tool '{tool_name}' not found",
                suggested_actions=[f"Available tools: {', '.join(self.list_tools())}"]
            )
        
        # First, try safe execution
        result = await tool.safe_execute(**kwargs)
        
        # If approval is required, ask for it
        if result.status == ToolResultStatus.REQUIRES_APPROVAL:
            if self._approval_callback:
                approved = self._approval_callback(tool_name, kwargs)
                if approved:
                    # Execute without safety checks
                    try:
                        validated_params = tool.validate_parameters(**kwargs)
                        result = await tool.execute(**validated_params)
                    except Exception as e:
                        result = ToolResult(
                            status=ToolResultStatus.ERROR,
                            error=str(e)
                        )
                else:
                    result.status = ToolResultStatus.CANCELLED
                    result.content = "Operation cancelled by user"
            else:
                # No approval callback - deny by default
                result.status = ToolResultStatus.CANCELLED
                result.content = "Operation requires approval but no approval mechanism available"
        
        return result
    
    def get_tool_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about all tools."""
        return {
            name: {
                "description": tool.description,
                "parameters": tool.parameters,
                "requires_approval": tool.requires_approval
            }
            for name, tool in self._tools.items()
        }


# Global tool registry
tool_registry = ToolRegistry()