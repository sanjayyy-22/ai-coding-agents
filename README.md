# AI Coding Agent

A terminal-based AI coding agent that implements the **Perceive → Reason → Act → Learn** loop for intelligent code interaction and development assistance.

## 🚀 Features

### Core Agent Architecture
- **Perceive**: Gather current state (file contents, git status, user intent)
- **Reason**: Use LLM to analyze situation and plan actions  
- **Act**: Execute tools safely with user oversight
- **Learn**: Update memory and context for future decisions

### Development Tools
- **Filesystem Operations**: Read, write, search, and manage files and directories
- **Git Integration**: Status, diff, commit, branch management, and more
- **Code Analysis**: Linting, dependency analysis, complexity analysis, security scans
- **Command Execution**: Run tests, builds, and other commands with safety controls

### Safety & Control
- **User Approval System**: All destructive operations require confirmation
- **Preview Mode**: See what will change before applying modifications  
- **Rollback Capability**: Undo agent actions when possible
- **Pattern Learning**: Remember user preferences for approval decisions

### Memory & Learning
- **Session Memory**: Current conversation context and working memory
- **Persistent Memory**: Long-term storage of patterns, preferences, and learnings
- **Semantic Search**: Find relevant past interactions and solutions
- **Pattern Recognition**: Learn from successful and failed interactions

### Multi-LLM Support
- **OpenAI**: GPT-4, GPT-3.5-turbo support
- **Anthropic**: Claude-3 family models
- **Local Models**: Ollama and OpenAI-compatible endpoints
- **Automatic Fallback**: Gracefully handle provider failures

## 📦 Installation

### Prerequisites
- Python 3.9 or higher
- Git
- API key for OpenAI, Anthropic, or local model setup

### Quick Setup

1. **Clone and Install**
```bash
git clone <repository-url>
cd ai-coding-agent
pip install -r requirements.txt
```

2. **Set API Key**
```bash
# For OpenAI
export OPENAI_API_KEY="your-api-key-here"

# For Anthropic  
export ANTHROPIC_API_KEY="your-api-key-here"

# For local models
export LLM_BASE_URL="http://localhost:11434"  # Ollama default
```

3. **Start the Agent**
```bash
python -m ai_coding_agent.cli start
```

### Alternative Installation
```bash
# Install as a package
pip install -e .

# Run from anywhere
agent start
```

## 🎯 Usage

### Interactive Mode
Start the agent for conversational interaction:
```bash
agent start
```

Example interactions:
```
💬 You: What files are in this directory?
🤖 Agent: I'll check the current directory for you...

💬 You: Add error handling to the login function in auth.py
🤖 Agent: I'll analyze the auth.py file and add appropriate error handling...

💬 You: Run the tests and fix any failures
🤖 Agent: I'll run the test suite and address any issues found...
```

### Single Command Mode
Send one-off commands:
```bash
agent chat "What's in package.json?"
agent chat "Create a new Python module for user authentication"
agent chat --stream "Explain this code structure"
```

### Configuration
```bash
# Show current configuration
agent config

# Set configuration values
agent set-config llm.provider openai
agent set-config llm.model gpt-4
agent set-config verbose true
```

### System Status
```bash
# Check system status
agent status

# Show memory statistics  
agent status --memory

# List available tools
agent status --tools

# Show LLM provider info
agent status --providers
```

### Memory Management
```bash
# Clear all memory
agent clear-memory

# Clear specific memory type
agent clear-memory --type conversation
```

## 🛠️ Configuration

The agent uses a YAML configuration file stored at `~/.ai_coding_agent/config.yaml`.

### Example Configuration
```yaml
name: CodeAssistant
version: 1.0.0

llm:
  provider: openai
  model: gpt-4
  api_key: null  # Set via environment variable
  base_url: null
  max_tokens: 4096
  temperature: 0.1

require_approval_for_destructive: true
auto_backup: true
max_file_size: 1000000
max_context_length: 8192
memory_persistence: true
verbose: false
color_output: true
streaming: true
```

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key  
- `LLM_BASE_URL`: Base URL for local/custom models
- `LLM_MODEL`: Model name override
- `LLM_PROVIDER`: Provider override

## 🔧 Available Tools

### Filesystem Tool
```
Operations: read, write, search, list, mkdir, delete, copy, move, exists
Safety: Automatic backups, approval for destructive operations
```

### Git Tool  
```
Operations: status, diff, add, commit, push, pull, branch, checkout, log, stash, reset
Safety: Preview changes, approval for push/reset operations
```

### Code Analysis Tool
```
Operations: lint, dependencies, complexity, security, structure, imports, functions, classes
Languages: Python, JavaScript, TypeScript (extensible)
Tools: flake8, pylint, black, eslint, tsc
```

### Execution Tool
```
Operations: run, test, build, install, start, stop, status
Safety: Command validation, approval for dangerous operations
Auto-detection: Test frameworks, build systems, package managers
```

## 🔐 Safety Framework

### Approval System
The agent implements a comprehensive approval system for potentially destructive operations:

- **File Operations**: Write, delete, move operations require approval
- **Git Operations**: Commits, pushes, resets require approval  
- **Command Execution**: Potentially dangerous commands require approval
- **Pattern Learning**: Remember user preferences for future decisions

### Risk Assessment
Each operation is assessed for risk level:
- **Low Risk**: Read operations, status checks
- **Medium Risk**: File modifications, safe commands
- **High Risk**: Deletions, system modifications, git pushes

### User Control
- **Interactive Approval**: Detailed prompts with risk assessment
- **Always/Never Rules**: Set permanent preferences for operation types
- **Preview Mode**: See exactly what will change before proceeding
- **Escape Hatches**: Always provide ways to cancel or undo

## 🧠 Memory System

### Session Memory
- Conversation history and context
- Recent tool executions and results
- Current working state
- Temporary user preferences

### Persistent Memory  
- Long-term learning patterns
- User preferences and coding style
- Successful solution patterns
- Error patterns and recovery strategies

### Learning Capabilities
- **Pattern Recognition**: Learn from successful interactions
- **Error Recovery**: Remember solutions to common problems
- **User Adaptation**: Adapt to individual coding styles and preferences
- **Context Building**: Build project-specific knowledge over time

## 📊 Example Workflows

### Code Review and Improvement
```
💬 You: Review the auth module and suggest improvements

🤖 Agent: I'll analyze your authentication module...
🔧 [filesystem] Reading auth.py...
🔧 [code_analysis] Running security scan...
🔧 [code_analysis] Checking complexity...

Based on my analysis:
1. Add input validation for email format
2. Implement rate limiting for login attempts  
3. Use secure password hashing (bcrypt)
4. Add proper error logging

Would you like me to implement these improvements?
```

### Bug Investigation
```
💬 You: The login endpoint is returning 500 errors

🤖 Agent: I'll investigate the login endpoint issue...
🔧 [filesystem] Reading server logs...
🔧 [git] Checking recent changes to auth code...
🔧 [execution] Running tests for auth module...

Found the issue: Missing null check in user validation.
🔧 [filesystem] Writing fix to auth.py...
🔧 [execution] Running tests to verify fix...

The fix has been applied and tests are now passing!
```

### Project Setup
```
💬 You: Set up a new FastAPI project with authentication

🤖 Agent: I'll help you set up a FastAPI project with authentication...
🔧 [filesystem] Creating project structure...
🔧 [filesystem] Creating requirements.txt...
🔧 [filesystem] Creating main.py with FastAPI setup...
🔧 [filesystem] Creating auth module...
🔧 [execution] Installing dependencies...

Your FastAPI project is ready! Key features:
- JWT authentication
- User registration and login
- Password hashing with bcrypt
- API documentation at /docs
```

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Coding Agent                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐     │
│  │ Terminal    │  │ Approval     │  │ Display         │     │
│  │ Interface   │  │ System       │  │ Manager         │     │
│  └─────────────┘  └──────────────┘  └─────────────────┘     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Core Agent Engine                          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │ │
│  │  │ Perceive │ │ Reason   │ │ Act      │ │ Learn    │   │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐    │
│  │ LLM          │  │ Memory       │  │ Tool Execution  │    │
│  │ Integration  │  │ Management   │  │ Engine          │    │
│  │              │  │              │  │                 │    │
│  │ • OpenAI     │  │ • Session    │  │ • Filesystem    │    │
│  │ • Anthropic  │  │ • Persistent │  │ • Git           │    │
│  │ • Local      │  │ • Learning   │  │ • Code Analysis │    │
│  │              │  │              │  │ • Execution     │    │
│  └──────────────┘  └──────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

- **SOLID Principles**: Clean, maintainable, extensible code
- **Safety First**: All operations require appropriate safeguards
- **Human in the Loop**: User maintains control over destructive operations  
- **Learning Oriented**: System improves through interaction
- **Tool Oriented**: Capabilities extended through tools, not hardcoded logic

## 🔬 Development

### Adding New Tools
```python
from ai_coding_agent.tools.base import BaseTool, ToolResult, ToolResultStatus

class MyCustomTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.name = "my_tool"
    
    @property
    def description(self) -> str:
        return "Description of what this tool does"
    
    @property  
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string", 
                    "description": "Description of parameter"
                }
            },
            "required": ["param1"]
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        # Tool implementation
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            content="Tool executed successfully"
        )

# Register the tool
tool_registry.register(MyCustomTool())
```

### Adding New LLM Providers
```python
from ai_coding_agent.llm.base import BaseLLMProvider, LLMResponse

class CustomLLMProvider(BaseLLMProvider):
    async def initialize(self) -> None:
        # Provider setup
        pass
    
    async def generate_response(self, messages, tools=None, **kwargs) -> LLMResponse:
        # Implementation
        pass
    
    async def stream_response(self, messages, tools=None, **kwargs):
        # Streaming implementation
        pass
```

## 🧪 Testing

### Running Tests
```bash
# Install test dependencies
pip install -e .[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=ai_coding_agent

# Run specific test file
pytest tests/test_agent.py
```

### Manual Testing
```bash
# Test basic functionality
agent chat "Hello, what can you do?"

# Test file operations
agent chat "List files in current directory"

# Test git operations  
agent chat "Show git status"

# Test with approval disabled (for testing)
agent start --no-approval
```

## 📈 Performance

### Optimization Features
- **Context Truncation**: Smart message history management
- **Memory Cleanup**: Automatic cleanup of old entries
- **Provider Fallback**: Automatic failover between LLM providers
- **Efficient Tool Execution**: Parallel tool execution where safe

### Resource Usage
- **Memory**: ~10-50MB base usage, scales with conversation length
- **Storage**: SQLite database for persistent memory (~1-10MB typical)
- **Network**: API calls only when needed, supports local models

## 🔧 Troubleshooting

### Common Issues

**"No LLM providers available"**
```bash
# Check API keys
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Test connection
agent status --providers
```

**"Tool execution failed"**
```bash
# Check tool availability
agent status --tools

# Check file permissions
ls -la

# Check git repository
git status
```

**"Memory initialization failed"**
```bash
# Clear corrupted memory
agent clear-memory

# Check disk space
df -h ~/.ai_coding_agent/
```

### Debug Mode
```bash
# Enable verbose logging
agent start --verbose

# Show detailed configuration
agent config
```

## 🤝 Contributing

We welcome contributions! Areas where help is needed:

- **New Tools**: Expand agent capabilities
- **LLM Providers**: Add support for new models
- **Safety Features**: Enhance security and user control
- **Documentation**: Improve guides and examples
- **Testing**: Add test coverage and scenarios

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for GPT models and function calling APIs
- Anthropic for Claude models and tool use capabilities  
- Rich library for beautiful terminal interfaces
- The open source community for foundational tools

---

**Built with ❤️ for developers who want an intelligent pair-programming partner.**
