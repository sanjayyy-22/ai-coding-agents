# 🚀 Quick Start Guide - Running AI Coding Agent Locally

This guide will help you get the AI Coding Agent running on your local machine in just a few minutes.

## Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed on your system
- **Git** (optional but recommended)
- An **OpenAI API key** OR **Anthropic API key** (get from their websites)

## Step 1: Download the Project

### Option A: If you have the project files locally
```bash
# Navigate to your project directory
cd /path/to/ai-coding-agent
```

### Option B: If you need to create the project structure
```bash
# Create a new directory
mkdir ai-coding-agent
cd ai-coding-agent

# You'll need to copy all the files from the workspace
# The project structure should look like this:
# ai-coding-agent/
# ├── src/
# ├── tests/
# ├── examples/
# ├── scripts/
# ├── pyproject.toml
# ├── requirements.txt
# └── README.md
```

## Step 2: Automated Setup (Recommended)

The easiest way is to use our setup script:

```bash
# Make the setup script executable
chmod +x scripts/setup_dev.sh

# Run the complete setup
./scripts/setup_dev.sh
```

This script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Set up configuration directory
- ✅ Run basic tests

## Step 3: Manual Setup (Alternative)

If you prefer manual setup or the script doesn't work:

### 3.1 Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate it (Linux/Mac)
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3.2 Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install the package and dependencies
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt
```

### 3.3 Create Configuration Directory
```bash
# Create config directory
mkdir -p ~/.ai_coding_agent

# Copy sample configuration
cp examples/sample_config.yaml ~/.ai_coding_agent/config.yaml
cp .env.example ~/.ai_coding_agent/.env
```

## Step 4: Configure API Keys

Edit the environment file with your API keys:

```bash
# Open the environment file
nano ~/.ai_coding_agent/.env

# Or use any text editor:
# code ~/.ai_coding_agent/.env
# vim ~/.ai_coding_agent/.env
```

Add your API keys:
```bash
# Choose ONE of these providers:

# For OpenAI (recommended)
OPENAI_API_KEY=your-openai-api-key-here
LLM_PROVIDER=openai

# For Anthropic Claude
ANTHROPIC_API_KEY=your-anthropic-api-key-here
LLM_PROVIDER=anthropic

# For local models (Ollama)
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama2
LLM_PROVIDER=local
```

### Getting API Keys:

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Create an account or sign in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

**Anthropic API Key:**
1. Go to https://console.anthropic.com/
2. Create an account or sign in
3. Go to "API Keys" section
4. Create a new key

## Step 5: Test the Installation

```bash
# Test the CLI is working
agent --help

# Check system status
agent status

# Test configuration
agent config
```

You should see output showing the agent is properly configured.

## Step 6: Start the Agent

```bash
# Start the interactive agent
agent start
```

You should see a welcome message and be able to interact with the agent:

```
🤖 AI Coding Agent v1.0.0
Type 'help' for commands, 'quit' to exit

💬 You: hello
🤖 Agent: Hello! I'm your AI Coding Agent. I can help you with:
- Reading and analyzing code files
- Git operations and version control
- Running tests and build commands
- Code analysis and improvements

What would you like to work on today?
```

## Step 7: First Commands to Try

Here are some safe commands to test the agent:

```bash
# In the agent interface:

# Check current directory
💬 You: what files are in the current directory?

# Read a file
💬 You: show me the contents of README.md

# Git status
💬 You: what's the git status of this repository?

# Help
💬 You: help
```

## Troubleshooting

### Common Issues:

**1. Python Version Error**
```bash
# Check Python version
python3 --version

# Should be 3.8 or higher
# If not, install a newer Python version
```

**2. Permission Denied**
```bash
# Make sure setup script is executable
chmod +x scripts/setup_dev.sh

# Check file permissions
ls -la scripts/setup_dev.sh
```

**3. Module Not Found**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall in development mode
pip install -e .
```

**4. API Key Issues**
```bash
# Check if API key is set
echo $OPENAI_API_KEY

# Verify environment file
cat ~/.ai_coding_agent/.env

# Test API connection
agent chat "hello" --no-interactive
```

**5. Dependencies Issues**
```bash
# Clean install
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Advanced Configuration

### Custom Configuration
Edit `~/.ai_coding_agent/config.yaml` to customize:
- Safety settings
- Memory limits
- Tool configurations
- Interface preferences

### Non-Interactive Mode
```bash
# Single command mode
agent chat "analyze this Python file: main.py"

# With specific options
agent chat "run tests" --provider openai --verbose
```

### Development Mode
```bash
# Run with verbose output
agent start --verbose

# Run with specific model
agent start --model gpt-4

# Disable approval for testing (be careful!)
agent start --no-approval
```

## What's Next?

Once you have the agent running:

1. **Explore the Examples**: Check `examples/demo_usage.md` for detailed usage examples
2. **Read the Documentation**: See `README.md` for comprehensive feature overview
3. **Run Tests**: Execute `pytest tests/` to ensure everything works
4. **Customize**: Modify `~/.ai_coding_agent/config.yaml` for your preferences

## Getting Help

- Type `help` in the agent interface for available commands
- Check `agent --help` for CLI options
- Read `docs/ARCHITECTURE.md` for technical details
- Review `examples/` for usage patterns

Enjoy coding with your new AI assistant! 🎉