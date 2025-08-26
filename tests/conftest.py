"""
Pytest configuration and shared fixtures for the AI Coding Agent test suite.
"""

import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import logging

# Add src to path for imports during testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Disable logging during tests to reduce noise
logging.getLogger("ai_coding_agent").setLevel(logging.CRITICAL)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write("Test content")
        temp_path = temp_file.name
    
    yield temp_path
    
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_python_file():
    """Create a sample Python file for testing."""
    content = '''
import os
import sys
from pathlib import Path

def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return "Hello, World!"

def complex_function(x, y, z=None):
    """A more complex function for testing."""
    if x > 10:
        if y < 5:
            if z is not None:
                return x + y + z
            else:
                return x + y
        else:
            return x * y
    else:
        return 0

class SampleClass:
    """A sample class for testing."""
    
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        return self.value
    
    def set_value(self, value):
        self.value = value

if __name__ == "__main__":
    hello_world()
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    yield temp_path
    
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_project_structure(temp_dir):
    """Create a sample project structure for testing."""
    project_dir = Path(temp_dir)
    
    # Create project files
    (project_dir / "README.md").write_text("# Sample Project\n\nThis is a test project.")
    (project_dir / "requirements.txt").write_text("requests>=2.25.0\nclick>=8.0.0\n")
    (project_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n.env\n")
    
    # Create source code structure
    src_dir = project_dir / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("")
    
    app_dir = src_dir / "app"
    app_dir.mkdir()
    (app_dir / "__init__.py").write_text("")
    (app_dir / "main.py").write_text("""
import click

@click.command()
def main():
    '''Main entry point for the application.'''
    click.echo('Hello, World!')

if __name__ == '__main__':
    main()
""")
    
    # Create tests directory
    tests_dir = project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_main.py").write_text("""
import pytest
from src.app.main import main

def test_main():
    '''Test the main function.'''
    # This is a placeholder test
    assert True
""")
    
    return project_dir


@pytest.fixture
def mock_git_repo(temp_dir):
    """Create a mock git repository for testing."""
    try:
        import git
        
        repo_dir = Path(temp_dir)
        repo = git.Repo.init(repo_dir)
        
        # Configure git (required for commits)
        with repo.config_writer() as git_config:
            git_config.set_value("user", "name", "Test User")
            git_config.set_value("user", "email", "test@example.com")
        
        # Create initial file
        test_file = repo_dir / "README.md"
        test_file.write_text("# Test Repository\n\nThis is a test repository.")
        
        # Add and commit
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")
        
        yield repo_dir
        
    except ImportError:
        pytest.skip("GitPython not available")


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response for testing."""
    def _create_response(content="Test response", function_calls=None):
        response = Mock()
        response.content = content
        response.function_calls = function_calls or []
        response.usage = Mock()
        response.usage.prompt_tokens = 50
        response.usage.completion_tokens = 25
        response.usage.total_tokens = 75
        return response
    
    return _create_response


@pytest.fixture
def mock_tool_result():
    """Create a mock tool result for testing."""
    def _create_result(status="success", content="Test result", metadata=None):
        from src.ai_coding_agent.tools.base import ToolResult
        return ToolResult(
            status=status,
            content=content,
            metadata=metadata or {}
        )
    
    return _create_result


@pytest.fixture
def mock_memory_entry():
    """Create a mock memory entry for testing."""
    def _create_entry(content="Test memory", memory_type="conversation", metadata=None):
        from src.ai_coding_agent.memory.base import MemoryEntry
        from datetime import datetime
        
        return MemoryEntry(
            id="test-id",
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
            created_at=datetime.now(),
            importance=1.0
        )
    
    return _create_entry


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    from src.ai_coding_agent.utils.config import AgentConfig
    
    config = AgentConfig()
    # Override with test-friendly settings
    config.safety.require_approval = False  # Auto-approve for tests
    config.memory.max_session_entries = 100
    config.interface.verbose = False
    
    return config


@pytest.fixture
def clean_environment():
    """Ensure clean environment variables for testing."""
    original_env = os.environ.copy()
    
    # Remove potentially interfering environment variables
    test_env_vars = [
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY', 
        'LLM_MODEL',
        'LLM_PROVIDER',
        'LLM_BASE_URL'
    ]
    
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def capture_logs():
    """Capture log messages during testing."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    logger = logging.getLogger("ai_coding_agent")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    logger.removeHandler(handler)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark tests in integration directories as integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
        
        # Mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


# Custom assertions
def assert_file_exists(path):
    """Assert that a file exists."""
    assert Path(path).exists(), f"File {path} does not exist"


def assert_file_contains(path, text):
    """Assert that a file contains specific text."""
    content = Path(path).read_text()
    assert text in content, f"File {path} does not contain '{text}'"


def assert_directory_structure(base_path, expected_structure):
    """Assert that a directory has the expected structure."""
    base = Path(base_path)
    
    for path in expected_structure:
        full_path = base / path
        assert full_path.exists(), f"Expected path {full_path} does not exist"