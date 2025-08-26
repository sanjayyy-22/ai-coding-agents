"""Display manager for rich terminal output."""

import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.layout import Layout
from rich.live import Live
from rich.status import Status
from ..utils.config import config_manager


class DisplayManager:
    """Manages rich terminal display and formatting."""
    
    def __init__(self):
        self.console = Console(color_system="auto" if config_manager.config.color_output else None)
        self.current_progress: Optional[Progress] = None
        self.current_status: Optional[Status] = None
    
    def print(self, *args, **kwargs) -> None:
        """Print with rich formatting."""
        self.console.print(*args, **kwargs)
    
    def print_panel(
        self, 
        content: Union[str, Text], 
        title: Optional[str] = None,
        style: str = "blue",
        border_style: str = "blue"
    ) -> None:
        """Print content in a panel."""
        panel = Panel(
            content,
            title=title,
            style=style,
            border_style=border_style,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def print_header(self, text: str, style: str = "bold blue") -> None:
        """Print a header."""
        self.console.print(f"\n{text}", style=style)
        self.console.print("─" * len(text), style=style)
    
    def print_error(self, message: str, details: Optional[str] = None) -> None:
        """Print an error message."""
        error_text = Text("ERROR: ", style="bold red")
        error_text.append(message, style="red")
        
        content = error_text
        if details:
            content = Text.assemble(error_text, "\n\n", details)
        
        self.print_panel(
            content,
            title="Error",
            style="red",
            border_style="red"
        )
    
    def print_warning(self, message: str, details: Optional[str] = None) -> None:
        """Print a warning message."""
        warning_text = Text("WARNING: ", style="bold yellow")
        warning_text.append(message, style="yellow")
        
        content = warning_text
        if details:
            content = Text.assemble(warning_text, "\n\n", details)
        
        self.print_panel(
            content,
            title="Warning",
            style="yellow",
            border_style="yellow"
        )
    
    def print_success(self, message: str, details: Optional[str] = None) -> None:
        """Print a success message."""
        success_text = Text("SUCCESS: ", style="bold green")
        success_text.append(message, style="green")
        
        content = success_text
        if details:
            content = Text.assemble(success_text, "\n\n", details)
        
        self.print_panel(
            content,
            title="Success",
            style="green",
            border_style="green"
        )
    
    def print_info(self, message: str, details: Optional[str] = None) -> None:
        """Print an info message."""
        info_text = Text("INFO: ", style="bold cyan")
        info_text.append(message, style="cyan")
        
        content = info_text
        if details:
            content = Text.assemble(info_text, "\n\n", details)
        
        self.print_panel(
            content,
            title="Information",
            style="cyan",
            border_style="cyan"
        )
    
    def print_code(
        self, 
        code: str, 
        language: str = "python",
        theme: str = "monokai",
        line_numbers: bool = True
    ) -> None:
        """Print syntax-highlighted code."""
        syntax = Syntax(
            code,
            language,
            theme=theme,
            line_numbers=line_numbers,
            word_wrap=True
        )
        self.console.print(syntax)
    
    def print_markdown(self, markdown_text: str) -> None:
        """Print markdown-formatted text."""
        md = Markdown(markdown_text)
        self.console.print(md)
    
    def print_table(
        self, 
        data: List[Dict[str, Any]], 
        title: Optional[str] = None,
        show_header: bool = True
    ) -> None:
        """Print data in a table format."""
        if not data:
            self.print("No data to display", style="dim")
            return
        
        table = Table(title=title, show_header=show_header)
        
        # Add columns
        if data:
            for key in data[0].keys():
                table.add_column(str(key).title(), style="cyan")
        
        # Add rows
        for row in data:
            table.add_row(*[str(value) for value in row.values()])
        
        self.console.print(table)
    
    def print_tree(self, root_data: Dict[str, Any], title: Optional[str] = None) -> None:
        """Print data in a tree format."""
        tree = Tree(title or "Data Structure")
        self._add_tree_nodes(tree, root_data)
        self.console.print(tree)
    
    def _add_tree_nodes(self, parent, data: Any) -> None:
        """Recursively add nodes to tree."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    branch = parent.add(f"[bold]{key}[/bold]")
                    self._add_tree_nodes(branch, value)
                else:
                    parent.add(f"{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    branch = parent.add(f"[bold][{i}][/bold]")
                    self._add_tree_nodes(branch, item)
                else:
                    parent.add(f"[{i}]: {item}")
        else:
            parent.add(str(data))
    
    def print_diff(self, old_content: str, new_content: str, filename: str = "") -> None:
        """Print a diff between two text contents."""
        import difflib
        
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        
        diff_text = Text()
        for line in diff:
            if line.startswith('+++') or line.startswith('---'):
                diff_text.append(line, style="bold")
            elif line.startswith('@@'):
                diff_text.append(line, style="cyan")
            elif line.startswith('+'):
                diff_text.append(line, style="green")
            elif line.startswith('-'):
                diff_text.append(line, style="red")
            else:
                diff_text.append(line)
        
        if diff_text.plain:
            self.print_panel(
                diff_text,
                title=f"Diff: {filename}" if filename else "Diff",
                style="white",
                border_style="white"
            )
        else:
            self.print("No differences found", style="dim")
    
    def start_progress(self, description: str = "Working...") -> Progress:
        """Start a progress display."""
        self.current_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        
        self.current_progress.start()
        return self.current_progress
    
    def stop_progress(self) -> None:
        """Stop the current progress display."""
        if self.current_progress:
            self.current_progress.stop()
            self.current_progress = None
    
    def start_status(self, status: str) -> Status:
        """Start a status spinner."""
        self.current_status = Status(status, console=self.console)
        self.current_status.start()
        return self.current_status
    
    def stop_status(self) -> None:
        """Stop the current status spinner."""
        if self.current_status:
            self.current_status.stop()
            self.current_status = None
    
    def print_agent_response(
        self, 
        response: str, 
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Print an agent response with formatting."""
        # Main response
        if response:
            self.print_panel(
                response,
                title="🤖 Agent Response",
                style="green",
                border_style="green"
            )
        
        # Tool calls
        if tool_calls:
            self.print_header("🔧 Tool Calls")
            for i, tool_call in enumerate(tool_calls, 1):
                tool_name = tool_call.get("function", {}).get("name", "unknown")
                self.print(f"{i}. [bold cyan]{tool_name}[/bold cyan]")
                
                # Show parameters if not too verbose
                params = tool_call.get("function", {}).get("arguments", {})
                if isinstance(params, str):
                    try:
                        import json
                        params = json.loads(params)
                    except:
                        pass
                
                if isinstance(params, dict) and len(str(params)) < 200:
                    for key, value in params.items():
                        self.print(f"   {key}: {value}", style="dim")
                elif params:
                    self.print(f"   Parameters: {str(params)[:100]}...", style="dim")
        
        # Metadata
        if metadata and config_manager.config.verbose:
            self.print_header("📊 Metadata")
            self.print_tree(metadata)
    
    def print_tool_result(
        self, 
        tool_name: str, 
        result: Dict[str, Any],
        success: bool = True
    ) -> None:
        """Print a tool execution result."""
        status_icon = "✅" if success else "❌"
        status_color = "green" if success else "red"
        
        title = f"{status_icon} {tool_name} Result"
        
        content = Text()
        
        # Main content
        if "content" in result:
            content.append(result["content"])
        
        # Error information
        if "error" in result and result["error"]:
            content.append("\n\nError: ", style="bold red")
            content.append(result["error"], style="red")
        
        # Additional data
        if "data" in result and result["data"]:
            data = result["data"]
            if isinstance(data, dict) and len(str(data)) < 500:
                content.append("\n\nData:\n")
                for key, value in data.items():
                    content.append(f"  {key}: {value}\n", style="dim")
        
        # Suggested actions
        if "suggested_actions" in result and result["suggested_actions"]:
            content.append("\n\nSuggested actions:\n", style="bold yellow")
            for action in result["suggested_actions"]:
                content.append(f"  • {action}\n", style="yellow")
        
        self.print_panel(
            content,
            title=title,
            style=status_color,
            border_style=status_color
        )
    
    def print_memory_stats(self, stats: Dict[str, Any]) -> None:
        """Print memory statistics."""
        self.print_header("🧠 Memory Statistics")
        
        if "session" in stats and "persistent" in stats:
            # Combined stats
            table = Table(title="Memory Usage")
            table.add_column("System", style="cyan")
            table.add_column("Entries", style="green")
            table.add_column("Memory (MB)", style="yellow")
            table.add_column("Avg Importance", style="magenta")
            
            for system_name, system_stats in stats.items():
                if hasattr(system_stats, 'total_entries'):
                    table.add_row(
                        system_name.title(),
                        str(system_stats.total_entries),
                        f"{system_stats.memory_usage_mb:.2f}",
                        f"{system_stats.avg_importance:.2f}"
                    )
            
            self.console.print(table)
        else:
            # Single system stats
            self.print_tree(stats)
    
    def print_system_info(self, info: Dict[str, Any]) -> None:
        """Print system information."""
        self.print_header("ℹ️  System Information")
        
        table = Table(show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in info.items():
            table.add_row(key.replace("_", " ").title(), str(value))
        
        self.console.print(table)
    
    def print_help(self, commands: Dict[str, str]) -> None:
        """Print help information."""
        self.print_header("🆘 Available Commands")
        
        table = Table()
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")
        
        for command, description in commands.items():
            table.add_row(command, description)
        
        self.console.print(table)
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        self.console.clear()
    
    def print_separator(self, char: str = "─", style: str = "dim") -> None:
        """Print a separator line."""
        width = self.console.size.width
        self.console.print(char * width, style=style)
    
    def ask_confirmation(self, message: str, default: bool = False) -> bool:
        """Ask for user confirmation."""
        default_str = "Y/n" if default else "y/N"
        response = self.console.input(f"{message} [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', 'true', '1']
    
    def print_streaming_response(self, text: str) -> None:
        """Print streaming text without newlines."""
        self.console.print(text, end="", highlight=False)
    
    def print_thinking(self, message: str = "Thinking...") -> None:
        """Print a thinking indicator."""
        self.console.print(f"💭 {message}", style="dim italic")


# Global display manager instance
display = DisplayManager()