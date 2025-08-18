#!/usr/bin/env bash

# Setup script for yt-summarize-bot local development
# This script automates the entire setup process for local Python development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.12"
POETRY_VERSION="1.8.5"

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  YouTube Summarizer Bot - Development Setup${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check Python version
print_status "Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION_INSTALLED=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python $PYTHON_VERSION_INSTALLED found"
else
    print_error "Python 3 not found. Please install Python 3.12 or higher."
    exit 1
fi

# Check and install Poetry
print_status "Checking Poetry installation..."
if ! command_exists poetry; then
    print_status "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -

    # Add Poetry to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"

    echo ""
    echo -e "${YELLOW}Please add Poetry to your PATH:${NC}"
    echo 'export PATH="$HOME/.local/bin:$PATH"'
    echo "Add this line to your ~/.bashrc or ~/.zshrc file"
    echo ""

    # Check if Poetry is now available
    if ! command_exists poetry; then
        print_error "Poetry installation failed or not in PATH"
        exit 1
    fi
fi
print_success "Poetry is installed"

# Configure Poetry
print_status "Configuring Poetry..."
poetry config virtualenvs.in-project true
print_success "Poetry configured to create .venv in project directory"

# Create virtual environment and install dependencies
print_status "Creating virtual environment and installing dependencies..."
poetry env use python${PYTHON_VERSION} 2>/dev/null || poetry env use python3
poetry install --with dev
print_success "Dependencies installed"

# Install pre-commit hooks
print_status "Installing pre-commit hooks..."
poetry run pre-commit install
print_success "Pre-commit hooks installed"

# Create .env file if it doesn't exist
print_status "Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    print_success ".env file created from template"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Edit .env file with your credentials:${NC}"
    echo "1. BOT_TOKEN - Get from @BotFather on Telegram"
    echo "2. AUTH_USER_ID - Get from @userinfobot on Telegram"
else
    print_success ".env file already exists"
fi

# Run initial code formatting
print_status "Running initial code formatting..."
poetry run black . 2>/dev/null || true
poetry run ruff check . --fix 2>/dev/null || true
print_success "Code formatting complete"

# Create convenience scripts
print_status "Creating convenience scripts..."

# Create run.sh
cat > run.sh << 'EOF'
#!/usr/bin/env bash
# Quick script to run the bot
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create it from .env.example"
    exit 1
fi
poetry run python -m yt_summarize_bot
EOF
chmod +x run.sh
print_success "Created run.sh"

# Create test.sh
cat > test.sh << 'EOF'
#!/usr/bin/env bash
# Run all tests and quality checks
echo "Running tests..."
poetry run pytest -v
echo ""
echo "Running linting..."
poetry run ruff check .
echo ""
echo "Running type checking..."
poetry run mypy yt_summarize_bot
echo ""
echo "Running black check..."
poetry run black --check .
EOF
chmod +x test.sh
print_success "Created test.sh"

echo ""
echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}  Setup Complete! 🎉${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Telegram credentials"
echo "   $ nano .env"
echo ""
echo "2. Run the bot:"
echo "   $ ./run.sh"
echo "   or"
echo "   $ make run"
echo "   or"
echo "   $ poetry run python -m yt_summarize_bot"
echo ""
echo "Available commands:"
echo "  make help      - Show all available make commands"
echo "  make test      - Run tests"
echo "  make format    - Format code"
echo "  make lint      - Run linting"
echo "  ./run.sh       - Run the bot"
echo "  ./test.sh      - Run all quality checks"
echo ""

# Activate virtual environment hint
if [ -d ".venv" ]; then
    echo "To activate the virtual environment manually:"
    echo "  $ source .venv/bin/activate"
    echo ""
fi
