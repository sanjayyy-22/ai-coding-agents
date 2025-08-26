#!/bin/bash

# AI Coding Agent - Development Setup Script
# This script sets up the development environment for the AI Coding Agent

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    print_status "Checking Python version..."
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    required_version="3.8"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_error "Python $python_version found, but Python $required_version or higher is required."
        exit 1
    fi
    
    print_success "Python $python_version found"
}

# Check if git is available
check_git() {
    print_status "Checking Git..."
    
    if ! command_exists git; then
        print_warning "Git is not installed. Some features may not work properly."
        print_warning "Please install Git: https://git-scm.com/downloads"
    else
        print_success "Git found"
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Skipping creation."
    else
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment not found. Please run create_venv first."
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install main dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Main dependencies installed"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
    
    # Install development dependencies
    if [ -f "pyproject.toml" ]; then
        pip install -e ".[dev]"
        print_success "Development dependencies installed"
    else
        print_warning "pyproject.toml not found, skipping development dependencies"
    fi
}

# Install package in development mode
install_package() {
    print_status "Installing package in development mode..."
    
    if [ -f "pyproject.toml" ]; then
        pip install -e .
        print_success "Package installed in development mode"
    else
        print_error "pyproject.toml not found"
        exit 1
    fi
}

# Setup pre-commit hooks (if available)
setup_precommit() {
    print_status "Setting up pre-commit hooks..."
    
    if command_exists pre-commit; then
        if [ -f ".pre-commit-config.yaml" ]; then
            pre-commit install
            print_success "Pre-commit hooks installed"
        else
            print_warning ".pre-commit-config.yaml not found, skipping pre-commit setup"
        fi
    else
        print_warning "pre-commit not found, skipping pre-commit setup"
        print_warning "Install with: pip install pre-commit"
    fi
}

# Create config directory
create_config_dir() {
    print_status "Creating configuration directory..."
    
    config_dir="$HOME/.ai_coding_agent"
    
    if [ ! -d "$config_dir" ]; then
        mkdir -p "$config_dir"
        print_success "Configuration directory created at $config_dir"
    else
        print_warning "Configuration directory already exists"
    fi
    
    # Copy sample config if it doesn't exist
    if [ ! -f "$config_dir/config.yaml" ] && [ -f "examples/sample_config.yaml" ]; then
        cp examples/sample_config.yaml "$config_dir/config.yaml"
        print_success "Sample configuration copied to $config_dir/config.yaml"
    fi
    
    # Copy environment example
    if [ ! -f "$config_dir/.env" ] && [ -f ".env.example" ]; then
        cp .env.example "$config_dir/.env"
        print_warning "Environment template copied to $config_dir/.env"
        print_warning "Please edit $config_dir/.env and add your API keys"
    fi
}

# Run basic tests
run_tests() {
    print_status "Running basic tests..."
    
    if command_exists pytest; then
        # Run a subset of fast tests
        if pytest tests/ -x -v --tb=short -m "not slow"; then
            print_success "Basic tests passed"
        else
            print_warning "Some tests failed. This might be due to missing API keys or dependencies."
        fi
    else
        print_warning "pytest not found, skipping tests"
    fi
}

# Check optional dependencies
check_optional_deps() {
    print_status "Checking optional dependencies..."
    
    optional_deps=(
        "black:Code formatting"
        "isort:Import sorting"
        "mypy:Type checking"
        "flake8:Linting"
        "pylint:Advanced linting"
    )
    
    for dep_info in "${optional_deps[@]}"; do
        IFS=':' read -r dep_name dep_desc <<< "$dep_info"
        if python3 -c "import $dep_name" 2>/dev/null; then
            print_success "$dep_desc ($dep_name) available"
        else
            print_warning "$dep_desc ($dep_name) not available"
        fi
    done
}

# Setup development environment info
show_setup_info() {
    echo
    print_success "Development environment setup complete!"
    echo
    echo "Next steps:"
    echo "1. Activate the virtual environment:"
    echo "   source venv/bin/activate"
    echo
    echo "2. Configure your API keys in:"
    echo "   ~/.ai_coding_agent/.env"
    echo
    echo "3. Test the installation:"
    echo "   agent --help"
    echo
    echo "4. Start the agent:"
    echo "   agent start"
    echo
    echo "5. Run tests:"
    echo "   pytest tests/"
    echo
    echo "6. Code formatting:"
    echo "   black src/ tests/"
    echo "   isort src/ tests/"
    echo
    echo "7. Type checking:"
    echo "   mypy src/"
    echo
}

# Main setup function
main() {
    echo "========================================="
    echo "AI Coding Agent - Development Setup"
    echo "========================================="
    echo
    
    # Check prerequisites
    check_python
    check_git
    
    # Setup virtual environment
    create_venv
    activate_venv
    
    # Install dependencies and package
    install_dependencies
    install_package
    
    # Setup additional development tools
    setup_precommit
    
    # Create configuration
    create_config_dir
    
    # Check optional dependencies
    check_optional_deps
    
    # Run basic tests
    run_tests
    
    # Show final information
    show_setup_info
}

# Parse command line arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "venv")
        create_venv
        activate_venv
        ;;
    "deps")
        activate_venv
        install_dependencies
        ;;
    "test")
        activate_venv
        run_tests
        ;;
    "clean")
        print_status "Cleaning up development environment..."
        rm -rf venv/
        rm -rf build/
        rm -rf dist/
        rm -rf *.egg-info/
        find . -type d -name __pycache__ -delete
        find . -type f -name "*.pyc" -delete
        print_success "Cleanup complete"
        ;;
    "help"|"-h"|"--help")
        echo "AI Coding Agent Development Setup Script"
        echo
        echo "Usage: $0 [command]"
        echo
        echo "Commands:"
        echo "  setup    Full development environment setup (default)"
        echo "  venv     Create and activate virtual environment only"
        echo "  deps     Install dependencies only"
        echo "  test     Run tests only"
        echo "  clean    Clean up build artifacts and cache"
        echo "  help     Show this help message"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac