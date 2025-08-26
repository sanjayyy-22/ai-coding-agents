"""Configuration management for the AI Coding Agent."""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""
    provider: str = Field(default="openai", description="LLM provider (openai, anthropic, local)")
    model: str = Field(default="gpt-4", description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    base_url: Optional[str] = Field(default=None, description="Custom base URL")
    max_tokens: int = Field(default=4096, description="Maximum tokens per request")
    temperature: float = Field(default=0.1, description="Temperature for responses")


class AgentConfig(BaseModel):
    """Main agent configuration."""
    
    # Core settings
    name: str = Field(default="CodeAssistant", description="Agent name")
    version: str = Field(default="1.0.0", description="Agent version")
    
    # LLM settings
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # Safety settings
    require_approval_for_destructive: bool = Field(default=True, description="Require approval for destructive operations")
    auto_backup: bool = Field(default=True, description="Create automatic backups")
    max_file_size: int = Field(default=1_000_000, description="Max file size to process (bytes)")
    
    # Memory settings
    max_context_length: int = Field(default=8192, description="Maximum context length")
    memory_persistence: bool = Field(default=True, description="Enable persistent memory")
    
    # Interface settings
    verbose: bool = Field(default=False, description="Verbose output")
    color_output: bool = Field(default=True, description="Colored terminal output")
    streaming: bool = Field(default=True, description="Stream responses")


class ConfigManager:
    """Manages configuration loading and saving."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.home() / ".ai_coding_agent" / "config.yaml"
        self.config_path.parent.mkdir(exist_ok=True)
        self._config: Optional[AgentConfig] = None
    
    def load_config(self) -> AgentConfig:
        """Load configuration from file or create default."""
        if self._config is not None:
            return self._config
            
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = yaml.safe_load(f)
                self._config = AgentConfig(**data)
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
                self._config = AgentConfig()
        else:
            self._config = AgentConfig()
            self.save_config()
        
        # Override with environment variables
        self._apply_env_overrides()
        return self._config
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        if self._config is None:
            return
            
        with open(self.config_path, 'w') as f:
            yaml.dump(self._config.model_dump(), f, default_flow_style=False)
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        if not self._config:
            return
            
        # LLM overrides
        if os.getenv("OPENAI_API_KEY"):
            self._config.llm.api_key = os.getenv("OPENAI_API_KEY")
            self._config.llm.provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            self._config.llm.api_key = os.getenv("ANTHROPIC_API_KEY")
            self._config.llm.provider = "anthropic"
        
        if os.getenv("LLM_MODEL"):
            self._config.llm.model = os.getenv("LLM_MODEL")
        
        if os.getenv("LLM_BASE_URL"):
            self._config.llm.base_url = os.getenv("LLM_BASE_URL")
            self._config.llm.provider = "local"
    
    @property
    def config(self) -> AgentConfig:
        """Get current configuration."""
        if self._config is None:
            self.load_config()
        return self._config
    
    def update_config(self, **kwargs) -> None:
        """Update configuration values."""
        if self._config is None:
            self.load_config()
        
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        
        self.save_config()


# Global config manager instance
config_manager = ConfigManager()