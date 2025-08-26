"""Command-line interface for the AI Coding Agent."""

import asyncio
import sys
import click
from pathlib import Path
from .core.agent import AICodeAgent
from .interface.terminal import TerminalInterface
from .interface.display import display
from .utils.config import config_manager


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """AI Coding Agent - Your intelligent pair-programming partner."""
    pass


@cli.command()
@click.option("--config", "-c", help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--provider", "-p", help="LLM provider (openai, anthropic, local)")
@click.option("--model", "-m", help="Model name")
@click.option("--no-approval", is_flag=True, help="Disable approval for destructive operations")
def start(config, verbose, provider, model, no_approval):
    """Start the AI Coding Agent terminal interface."""
    
    # Update configuration
    if verbose:
        config_manager.update_config(verbose=True)
    
    if provider:
        config_manager.config.llm.provider = provider
    
    if model:
        config_manager.config.llm.model = model
    
    if no_approval:
        config_manager.update_config(require_approval_for_destructive=False)
    
    # Show startup info
    display.print_panel(
        "🤖 Starting AI Coding Agent...",
        title="Initialization",
        style="cyan",
        border_style="cyan"
    )
    
    # Check for API keys
    if not _check_api_keys():
        display.print_error(
            "No LLM API keys found. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.",
            "You can also use a local model by setting LLM_BASE_URL."
        )
        sys.exit(1)
    
    # Create and start agent
    agent = AICodeAgent()
    interface = TerminalInterface(agent)
    
    try:
        asyncio.run(interface.start())
    except KeyboardInterrupt:
        display.print("\n👋 Agent stopped", style="yellow")
    except Exception as e:
        display.print_error(f"Failed to start agent: {e}")
        sys.exit(1)


@cli.command()
def config():
    """Show current configuration."""
    config_dict = config_manager.config.model_dump()
    display.print_header("⚙️ Current Configuration")
    display.print_tree(config_dict)


@cli.command()
@click.option("--key", "-k", required=True, help="Configuration key")
@click.option("--value", "-v", required=True, help="Configuration value")
def set_config(key, value):
    """Set a configuration value."""
    try:
        # Handle nested keys (e.g., llm.provider)
        keys = key.split(".")
        current = config_manager.config
        
        # Navigate to the parent object
        for k in keys[:-1]:
            current = getattr(current, k)
        
        # Set the value
        setattr(current, keys[-1], value)
        config_manager.save_config()
        
        display.print_success(f"Set {key} = {value}")
    except Exception as e:
        display.print_error(f"Failed to set configuration: {e}")


@cli.command()
@click.argument("message")
@click.option("--stream", "-s", is_flag=True, help="Stream response")
def chat(message, stream):
    """Send a single message to the agent (non-interactive mode)."""
    
    async def single_chat():
        agent = AICodeAgent()
        await agent.initialize()
        
        if stream:
            display.print("🤖 Agent: ", style="green", end="")
            async for chunk in agent.stream_response(message):
                display.print_streaming_response(chunk)
            display.print("")  # New line
        else:
            response = await agent.process_message(message)
            display.print_agent_response(
                response.get("content", ""),
                response.get("tool_calls"),
                response.get("metadata")
            )
    
    try:
        asyncio.run(single_chat())
    except KeyboardInterrupt:
        display.print("\nChat interrupted", style="yellow")
    except Exception as e:
        display.print_error(f"Chat failed: {e}")


@cli.command()
@click.option("--memory", is_flag=True, help="Show memory statistics")
@click.option("--tools", is_flag=True, help="Show available tools")
@click.option("--providers", is_flag=True, help="Show LLM provider info")
def status(memory, tools, providers):
    """Show system status and diagnostics."""
    
    async def show_status():
        agent = AICodeAgent()
        await agent.initialize()
        
        # Basic status
        display.print_header("🔍 System Status")
        display.print(f"✅ Agent initialized: {agent._initialized}")
        display.print(f"🧠 Memory system: {'Active' if agent.memory_manager._initialized else 'Not initialized'}")
        display.print(f"🔧 Tools available: {len(agent.tool_registry.list_tools())}")
        
        if providers:
            display.print_header("🤖 LLM Providers")
            provider_info = agent.llm_manager.get_provider_info()
            display.print_tree(provider_info)
        
        if tools:
            display.print_header("🔧 Available Tools")
            tool_info = agent.tool_registry.get_tool_info()
            for tool_name, info in tool_info.items():
                display.print(f"\n[bold cyan]{tool_name}[/bold cyan]")
                display.print(f"  {info['description']}")
        
        if memory:
            display.print_header("🧠 Memory Statistics")
            try:
                stats = await agent.memory_manager.get_stats()
                display.print_memory_stats(stats)
            except Exception as e:
                display.print_error(f"Failed to get memory stats: {e}")
    
    try:
        asyncio.run(show_status())
    except Exception as e:
        display.print_error(f"Status check failed: {e}")


@cli.command()
@click.option("--type", "-t", help="Memory type to clear")
@click.confirmation_option(prompt="Are you sure you want to clear memory?")
def clear_memory(type):
    """Clear agent memory."""
    
    async def clear():
        agent = AICodeAgent()
        await agent.initialize()
        
        from .memory.base import MemoryType
        memory_type = None
        if type:
            try:
                memory_type = MemoryType(type)
            except ValueError:
                display.print_error(f"Unknown memory type: {type}")
                return
        
        await agent.memory_manager.clear(memory_type)
        display.print_success("Memory cleared successfully")
    
    try:
        asyncio.run(clear())
    except Exception as e:
        display.print_error(f"Failed to clear memory: {e}")


@cli.command()
def install_deps():
    """Install required dependencies."""
    import subprocess
    
    display.print("📦 Installing dependencies...", style="cyan")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        display.print_success("Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        display.print_error(f"Failed to install dependencies: {e}")
    except FileNotFoundError:
        display.print_error("requirements.txt not found")


def _check_api_keys() -> bool:
    """Check if API keys are available."""
    import os
    
    # Check for OpenAI API key
    if os.getenv("OPENAI_API_KEY"):
        return True
    
    # Check for Anthropic API key
    if os.getenv("ANTHROPIC_API_KEY"):
        return True
    
    # Check for local model URL
    if os.getenv("LLM_BASE_URL"):
        return True
    
    return False


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()