"""
Comprehensive test suite for the AI Coding Agent.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import json

from src.ai_coding_agent.core.agent import AICodeAgent
from src.ai_coding_agent.llm.manager import LLMManager
from src.ai_coding_agent.memory.manager import MemoryManager
from src.ai_coding_agent.tools.registry import ToolRegistry
from src.ai_coding_agent.utils.config import ConfigManager, AgentConfig


class TestAICodeAgent:
    """Test the main AI Coding Agent functionality."""

    @pytest.fixture
    async def mock_llm_manager(self):
        """Create a mock LLM manager."""
        manager = Mock(spec=LLMManager)
        manager.generate_response = AsyncMock()
        manager.stream_response = AsyncMock()
        manager.count_tokens = Mock(return_value=100)
        manager.truncate_context = Mock(return_value=[])
        return manager

    @pytest.fixture
    async def mock_memory_manager(self):
        """Create a mock memory manager."""
        manager = Mock(spec=MemoryManager)
        manager.get_context = Mock(return_value=[])
        manager.store = AsyncMock()
        manager.learn_from_interaction = AsyncMock()
        return manager

    @pytest.fixture
    async def mock_tool_registry(self):
        """Create a mock tool registry."""
        registry = Mock(spec=ToolRegistry)
        registry.get_function_definitions = Mock(return_value=[])
        registry.execute_tool = AsyncMock()
        return registry

    @pytest.fixture
    async def agent(self, mock_llm_manager, mock_memory_manager, mock_tool_registry):
        """Create an agent with mocked dependencies."""
        with patch('src.ai_coding_agent.core.agent.LLMManager', return_value=mock_llm_manager), \
             patch('src.ai_coding_agent.core.agent.MemoryManager', return_value=mock_memory_manager), \
             patch('src.ai_coding_agent.core.agent.ToolRegistry', return_value=mock_tool_registry):
            
            config = AgentConfig()
            agent = AICodeAgent(config)
            return agent

    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent is not None
        assert hasattr(agent, 'llm_manager')
        assert hasattr(agent, 'memory_manager')
        assert hasattr(agent, 'tool_registry')

    async def test_process_message_simple(self, agent):
        """Test processing a simple message."""
        # Mock LLM response
        agent.llm_manager.generate_response.return_value = Mock(
            content="Hello! I'm ready to help with your coding tasks.",
            function_calls=[]
        )
        
        response = await agent.process_message("Hello!")
        
        assert "Hello!" in response
        agent.llm_manager.generate_response.assert_called_once()
        agent.memory_manager.store.assert_called()

    async def test_process_message_with_tool_call(self, agent):
        """Test processing a message that requires tool execution."""
        # Mock LLM response with function call
        mock_function_call = Mock()
        mock_function_call.name = "filesystem"
        mock_function_call.arguments = '{"operation": "read", "path": "test.py"}'
        
        agent.llm_manager.generate_response.return_value = Mock(
            content="I'll read the file for you.",
            function_calls=[mock_function_call]
        )
        
        # Mock tool execution result
        agent.tool_registry.execute_tool.return_value = Mock(
            status="success",
            content="def hello():\n    print('Hello, World!')",
            metadata={}
        )
        
        response = await agent.process_message("Read test.py")
        
        assert response is not None
        agent.tool_registry.execute_tool.assert_called_once()

    async def test_error_handling(self, agent):
        """Test error handling in message processing."""
        # Mock LLM to raise an exception
        agent.llm_manager.generate_response.side_effect = Exception("LLM Error")
        
        response = await agent.process_message("Test message")
        
        assert "error" in response.lower()
        assert "llm error" in response.lower()


class TestLLMManager:
    """Test the LLM Manager functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AgentConfig()

    @pytest.fixture
    def llm_manager(self, config):
        """Create LLM manager with test config."""
        return LLMManager(config.llm)

    def test_provider_initialization(self, llm_manager):
        """Test that providers are initialized correctly."""
        assert hasattr(llm_manager, 'providers')
        assert 'openai' in llm_manager.providers
        assert 'anthropic' in llm_manager.providers
        assert 'local' in llm_manager.providers

    async def test_generate_response_fallback(self, llm_manager):
        """Test fallback behavior when primary provider fails."""
        # Mock primary provider to fail
        llm_manager.providers['openai'].generate_response = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        # Mock fallback provider to succeed
        llm_manager.providers['anthropic'].generate_response = AsyncMock(
            return_value=Mock(content="Fallback response")
        )
        
        messages = [{"role": "user", "content": "Test"}]
        response = await llm_manager.generate_response(messages)
        
        assert response.content == "Fallback response"

    def test_token_counting(self, llm_manager):
        """Test token counting functionality."""
        text = "This is a test message for token counting."
        tokens = llm_manager.count_tokens(text)
        
        assert isinstance(tokens, int)
        assert tokens > 0


class TestMemoryManager:
    """Test the Memory Manager functionality."""

    @pytest.fixture
    async def memory_manager(self):
        """Create memory manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = AgentConfig()
            # Override memory path for testing
            config.memory.persistent_path = os.path.join(temp_dir, "test_memory.db")
            
            manager = MemoryManager(config.memory)
            await manager.initialize()
            yield manager
            await manager.close()

    async def test_store_and_retrieve(self, memory_manager):
        """Test storing and retrieving memories."""
        # Store a memory
        await memory_manager.store(
            content="Test memory",
            memory_type="conversation",
            metadata={"test": True}
        )
        
        # Retrieve memories
        memories = await memory_manager.get_recent(limit=5)
        
        assert len(memories) > 0
        assert memories[0].content == "Test memory"
        assert memories[0].metadata["test"] is True

    async def test_context_management(self, memory_manager):
        """Test context management functionality."""
        # Add some context entries
        await memory_manager.store(
            content="Important context 1",
            memory_type="context"
        )
        await memory_manager.store(
            content="Important context 2", 
            memory_type="context"
        )
        
        context = memory_manager.get_context()
        
        assert len(context) >= 2


class TestToolRegistry:
    """Test the Tool Registry functionality."""

    @pytest.fixture
    def tool_registry(self):
        """Create tool registry for testing."""
        registry = ToolRegistry()
        # Add test tools
        from src.ai_coding_agent.tools.filesystem import FileSystemTool
        registry.register_tool("filesystem", FileSystemTool())
        return registry

    def test_tool_registration(self, tool_registry):
        """Test tool registration."""
        assert "filesystem" in tool_registry.tools
        
    def test_function_definitions(self, tool_registry):
        """Test function definition generation."""
        definitions = tool_registry.get_function_definitions()
        
        assert isinstance(definitions, list)
        assert len(definitions) > 0
        assert any(func["name"] == "filesystem" for func in definitions)

    async def test_tool_execution(self, tool_registry):
        """Test tool execution with approval."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Test content")
            temp_path = temp_file.name
        
        try:
            # Mock approval callback to auto-approve
            tool_registry.approval_callback = Mock(return_value=True)
            
            result = await tool_registry.execute_tool(
                "filesystem",
                {"operation": "read", "path": temp_path}
            )
            
            assert result.status == "success"
            assert "Test content" in result.content
            
        finally:
            os.unlink(temp_path)


class TestFileSystemTool:
    """Test the FileSystem Tool functionality."""

    @pytest.fixture
    def filesystem_tool(self):
        """Create filesystem tool for testing."""
        from src.ai_coding_agent.tools.filesystem import FileSystemTool
        return FileSystemTool()

    async def test_read_file(self, filesystem_tool):
        """Test reading a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write("Hello, World!")
            temp_path = temp_file.name
        
        try:
            result = await filesystem_tool.execute({
                "operation": "read",
                "path": temp_path
            })
            
            assert result.status == "success"
            assert "Hello, World!" in result.content
            
        finally:
            os.unlink(temp_path)

    async def test_write_file(self, filesystem_tool):
        """Test writing a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "test.txt")
            
            result = await filesystem_tool.execute({
                "operation": "write",
                "path": temp_path,
                "content": "New content"
            })
            
            assert result.status == "success"
            
            # Verify file was written
            with open(temp_path, 'r') as f:
                content = f.read()
            assert content == "New content"

    async def test_list_directory(self, filesystem_tool):
        """Test listing directory contents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            Path(temp_dir, "file1.txt").touch()
            Path(temp_dir, "file2.py").touch()
            Path(temp_dir, "subdir").mkdir()
            
            result = await filesystem_tool.execute({
                "operation": "list",
                "path": temp_dir
            })
            
            assert result.status == "success"
            assert "file1.txt" in result.content
            assert "file2.py" in result.content
            assert "subdir" in result.content

    def test_safety_checks(self, filesystem_tool):
        """Test safety checks for operations."""
        # Test that dangerous operations are flagged
        assert not filesystem_tool.is_safe_operation({
            "operation": "delete",
            "path": "/"
        })
        
        assert not filesystem_tool.is_safe_operation({
            "operation": "write",
            "path": "/etc/passwd"
        })
        
        # Test that safe operations are allowed
        assert filesystem_tool.is_safe_operation({
            "operation": "read",
            "path": "safe_file.txt"
        })


class TestGitTool:
    """Test the Git Tool functionality."""

    @pytest.fixture
    def git_tool(self):
        """Create git tool for testing."""
        from src.ai_coding_agent.tools.git import GitTool
        return GitTool()

    @pytest.fixture
    def git_repo(self):
        """Create a test git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize git repo
            import git
            repo = git.Repo.init(temp_dir)
            
            # Create initial commit
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("Initial content")
            
            repo.index.add([test_file])
            repo.index.commit("Initial commit")
            
            yield temp_dir

    async def test_git_status(self, git_tool, git_repo):
        """Test git status operation."""
        result = await git_tool.execute({
            "operation": "status",
            "repo_path": git_repo
        })
        
        assert result.status == "success"
        assert "clean" in result.content.lower() or "nothing to commit" in result.content.lower()

    async def test_git_log(self, git_tool, git_repo):
        """Test git log operation."""
        result = await git_tool.execute({
            "operation": "log",
            "repo_path": git_repo,
            "max_entries": 5
        })
        
        assert result.status == "success"
        assert "Initial commit" in result.content

    def test_git_safety_checks(self, git_tool):
        """Test git safety checks."""
        # Test that dangerous operations require approval
        assert not git_tool.is_safe_operation({
            "operation": "reset",
            "hard": True
        })
        
        assert not git_tool.is_safe_operation({
            "operation": "push",
            "force": True
        })
        
        # Test that safe operations are allowed
        assert git_tool.is_safe_operation({
            "operation": "status"
        })
        
        assert git_tool.is_safe_operation({
            "operation": "log"
        })


class TestCodeAnalysisTool:
    """Test the Code Analysis Tool functionality."""

    @pytest.fixture
    def code_tool(self):
        """Create code analysis tool for testing."""
        from src.ai_coding_agent.tools.code import CodeAnalysisTool
        return CodeAnalysisTool()

    async def test_lint_python_code(self, code_tool):
        """Test linting Python code."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("""
def hello():
    print("Hello, World!")
    
def unused_function():
    pass
""")
            temp_path = temp_file.name
        
        try:
            result = await code_tool.execute({
                "operation": "lint",
                "path": temp_path
            })
            
            assert result.status in ["success", "warning"]  # Warnings are OK for linting
            
        finally:
            os.unlink(temp_path)

    async def test_analyze_dependencies(self, code_tool):
        """Test dependency analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("""
import os
import sys
from pathlib import Path
import requests
""")
            temp_path = temp_file.name
        
        try:
            result = await code_tool.execute({
                "operation": "dependencies",
                "path": temp_path
            })
            
            assert result.status == "success"
            assert "os" in result.content
            assert "requests" in result.content
            
        finally:
            os.unlink(temp_path)

    async def test_complexity_analysis(self, code_tool):
        """Test code complexity analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("""
def simple_function():
    return "Hello"

def complex_function(x):
    if x > 10:
        if x > 20:
            if x > 30:
                return "very high"
            else:
                return "high"
        else:
            return "medium"
    else:
        return "low"
""")
            temp_path = temp_file.name
        
        try:
            result = await code_tool.execute({
                "operation": "complexity",
                "path": temp_path
            })
            
            assert result.status == "success"
            
        finally:
            os.unlink(temp_path)


class TestConfigManager:
    """Test the Configuration Manager functionality."""

    def test_default_config(self):
        """Test default configuration loading."""
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        assert isinstance(config, AgentConfig)
        assert config.llm.provider in ["openai", "anthropic", "local"]
        assert config.safety.require_approval is True

    def test_environment_override(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'LLM_MODEL': 'gpt-3.5-turbo',
            'LLM_TEMPERATURE': '0.5'
        }):
            config_manager = ConfigManager()
            config = config_manager.get_config()
            
            assert config.llm.model == 'gpt-3.5-turbo'
            assert config.llm.temperature == 0.5

    def test_config_validation(self):
        """Test configuration validation."""
        config_manager = ConfigManager()
        
        # Test invalid configuration
        with pytest.raises(Exception):
            config_manager.load_from_dict({
                "llm": {
                    "temperature": 2.0  # Invalid: should be 0.0-1.0
                }
            })


if __name__ == "__main__":
    pytest.main([__file__, "-v"])