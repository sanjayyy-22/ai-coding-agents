"""Main terminal interface for the AI Coding Agent."""

import asyncio
import signal
import sys
from typing import Dict, List, Any, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from .display import display
from .approval import approval_system, ApprovalType, ApprovalResult


class TerminalInterface:
    """Main terminal interface for the AI Coding Agent."""
    
    def __init__(self, agent):
        self.agent = agent
        self.session = PromptSession(
            history=InMemoryHistory(),
            auto_suggest=AutoSuggestFromHistory(),
            complete_style="column"
        )
        self.running = False
        self.commands = {
            "help": "Show available commands",
            "quit": "Exit the agent",
            "clear": "Clear the screen", 
            "status": "Show system status",
            "memory": "Show memory statistics",
            "tools": "List available tools",
            "config": "Show configuration",
            "approve": "Manage approval settings"
        }
    
    async def start(self) -> None:
        """Start the terminal interface."""
        self.running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Show welcome message
        self._show_welcome()
        
        # Main interaction loop
        try:
            while self.running:
                await self._interaction_loop()
        except KeyboardInterrupt:
            pass
        finally:
            await self._cleanup()
    
    def _show_welcome(self) -> None:
        """Show welcome message."""
        welcome_text = """
🤖 AI Coding Agent v1.0.0

Your intelligent pair-programming partner that understands context,
learns from interactions, and helps with development tasks.

Type 'help' for available commands or just start chatting!
        """
        
        display.print_panel(
            welcome_text.strip(),
            title="Welcome",
            style="bold cyan",
            border_style="cyan"
        )
        
        # Show initial status
        display.print(f"🔧 Tools available: {len(self.agent.tool_registry.list_tools())}")
        display.print(f"🧠 Memory system: {'Active' if self.agent.memory_manager._initialized else 'Initializing'}")
        display.print(f"🤖 LLM provider: {self.agent.llm_manager.primary_provider or 'Not configured'}")
        display.print_separator()
    
    async def _interaction_loop(self) -> None:
        """Main interaction loop."""
        try:
            # Get user input
            user_input = await self._get_user_input()
            
            if not user_input.strip():
                return
            
            # Handle special commands
            if await self._handle_special_commands(user_input):
                return
            
            # Process with agent
            await self._process_user_input(user_input)
            
        except EOFError:
            self.running = False
        except KeyboardInterrupt:
            display.print("\nUse 'quit' to exit gracefully", style="yellow")
    
    async def _get_user_input(self) -> str:
        """Get user input with nice prompt."""
        try:
            # Create completer for commands
            completer = WordCompleter(
                list(self.commands.keys()) + self.agent.tool_registry.list_tools(),
                ignore_case=True
            )
            
            # Get input with async support
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.session.prompt(
                    "💬 You: ",
                    completer=completer
                )
            )
        except Exception as e:
            display.print_error(f"Input error: {e}")
            return ""
    
    async def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special commands. Returns True if command was handled."""
        command = user_input.strip().lower()
        
        if command == "help":
            display.print_help(self.commands)
            return True
        
        elif command in ["quit", "exit", "bye"]:
            display.print("👋 Goodbye!", style="cyan")
            self.running = False
            return True
        
        elif command == "clear":
            display.clear_screen()
            self._show_welcome()
            return True
        
        elif command == "status":
            await self._show_status()
            return True
        
        elif command == "memory":
            await self._show_memory_stats()
            return True
        
        elif command == "tools":
            await self._show_tools()
            return True
        
        elif command == "config":
            await self._show_config()
            return True
        
        elif command.startswith("approve"):
            await self._handle_approval_command(command)
            return True
        
        return False
    
    async def _process_user_input(self, user_input: str) -> None:
        """Process user input with the agent."""
        display.print_separator()
        display.print_thinking("Processing your request...")
        
        try:
            # Get agent response
            response = await self.agent.process_message(user_input)
            
            # Display response
            display.print_agent_response(
                response.get("content", ""),
                response.get("tool_calls"),
                response.get("metadata") if display.console.size.width > 120 else None
            )
            
        except Exception as e:
            display.print_error(f"Processing error: {e}")
            
            # Suggest recovery actions
            display.print("\nPossible solutions:", style="yellow")
            display.print("• Check your LLM configuration", style="dim")
            display.print("• Verify network connectivity", style="dim")
            display.print("• Try a simpler request", style="dim")
        
        display.print_separator()
    
    async def _show_status(self) -> None:
        """Show system status."""
        status_info = {
            "Agent Status": "Running" if self.running else "Stopped",
            "LLM Provider": self.agent.llm_manager.primary_provider or "Not configured",
            "Available Tools": len(self.agent.tool_registry.list_tools()),
            "Memory Initialized": self.agent.memory_manager._initialized,
            "Session Time": "TODO",  # Could track uptime
        }
        
        display.print_system_info(status_info)
        
        # Show provider info
        provider_info = self.agent.llm_manager.get_provider_info()
        if provider_info:
            display.print_header("🤖 LLM Provider Details")
            display.print_tree(provider_info)
    
    async def _show_memory_stats(self) -> None:
        """Show memory statistics."""
        try:
            stats = await self.agent.memory_manager.get_stats()
            display.print_memory_stats(stats)
            
            # Show recent memories
            recent = await self.agent.memory_manager.get_recent(5)
            if recent:
                display.print_header("📝 Recent Memories")
                for i, entry in enumerate(recent, 1):
                    display.print(f"{i}. [{entry.type.value}] {entry.content[:100]}...", style="dim")
        
        except Exception as e:
            display.print_error(f"Failed to get memory stats: {e}")
    
    async def _show_tools(self) -> None:
        """Show available tools."""
        tool_info = self.agent.tool_registry.get_tool_info()
        
        if not tool_info:
            display.print("No tools available", style="yellow")
            return
        
        display.print_header("🔧 Available Tools")
        
        for tool_name, info in tool_info.items():
            display.print(f"\n[bold cyan]{tool_name}[/bold cyan]")
            display.print(f"  Description: {info['description']}")
            display.print(f"  Requires Approval: {'Yes' if info['requires_approval'] else 'No'}")
    
    async def _show_config(self) -> None:
        """Show configuration."""
        from ..utils.config import config_manager
        
        config_dict = config_manager.config.model_dump()
        display.print_header("⚙️  Configuration")
        display.print_tree(config_dict)
    
    async def _handle_approval_command(self, command: str) -> None:
        """Handle approval-related commands."""
        parts = command.split()
        
        if len(parts) == 1:
            # Show approval stats
            stats = approval_system.get_approval_stats()
            display.print_header("🔐 Approval System Status")
            display.print_tree(stats)
        
        elif len(parts) >= 2:
            subcommand = parts[1]
            
            if subcommand == "clear":
                approval_system.clear_approval_rules()
                display.print_success("Cleared all approval rules")
            
            elif subcommand == "export":
                rules = approval_system.export_approval_rules()
                display.print_header("📤 Approval Rules Export")
                display.print_tree(rules)
            
            else:
                display.print("Unknown approval command. Available: clear, export", style="yellow")
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle system signals."""
        display.print(f"\nReceived signal {signum}", style="yellow")
        self.running = False
    
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        display.print("🧹 Cleaning up...", style="dim")
        
        try:
            # Close memory manager
            await self.agent.memory_manager.close()
            
            # Any other cleanup
            display.print("✅ Cleanup complete", style="green")
        
        except Exception as e:
            display.print_error(f"Cleanup error: {e}")


# Approval callback integration
def _approval_callback(tool_name: str, parameters: Dict[str, Any]) -> bool:
    """Approval callback for tools."""
    # Determine approval type based on tool and parameters
    approval_type = ApprovalType.DESTRUCTIVE_OPERATION
    
    if tool_name == "filesystem":
        operation = parameters.get("operation", "")
        if operation == "write":
            approval_type = ApprovalType.FILE_WRITE
        elif operation == "delete":
            approval_type = ApprovalType.FILE_DELETE
    elif tool_name == "git":
        approval_type = ApprovalType.GIT_OPERATION
    elif tool_name == "execution":
        approval_type = ApprovalType.COMMAND_EXECUTION
    
    # Request approval
    result = approval_system.request_approval(
        approval_type,
        f"Execute {tool_name} tool",
        parameters,
        str(parameters) if len(str(parameters)) < 500 else None
    )
    
    return result in [ApprovalResult.APPROVED, ApprovalResult.ALWAYS_ALLOW]