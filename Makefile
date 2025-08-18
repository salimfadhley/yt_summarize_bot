# Makefile for yt-summarize-bot local development

.PHONY: help install setup dev clean test lint format typecheck precommit run docker-build docker-run

# Python version
PYTHON_VERSION = 3.12

# Poetry version
POETRY_VERSION = 1.8.5

# Virtual environment name
VENV_NAME = .venv

# Default target
help:
	@echo "Available commands:"
	@echo "  make install       - Install Poetry and project dependencies"
	@echo "  make setup         - Full setup: install + pre-commit hooks"
	@echo "  make dev           - Setup development environment from scratch"
	@echo "  make clean         - Remove virtual environment and cache files"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linting (ruff)"
	@echo "  make format        - Format code with black"
	@echo "  make typecheck     - Run type checking with mypy"
	@echo "  make precommit     - Run all pre-commit hooks"
	@echo "  make run           - Run the bot locally"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run with docker-compose"
	@echo "  make recreate-env  - Force recreate virtual environment"

# Check if Poetry is installed
check-poetry:
	@command -v poetry >/dev/null 2>&1 || { \
		echo "Poetry not found. Installing Poetry..."; \
		curl -sSL https://install.python-poetry.org | python3 -; \
		echo "Please add Poetry to your PATH and run 'make install' again"; \
		exit 1; \
	}

# Install dependencies with Poetry
install: check-poetry
	@echo "Configuring Poetry for in-project virtual environment..."
	poetry config virtualenvs.in-project true
	@echo "Installing project dependencies..."
	poetry env use python$(PYTHON_VERSION) || poetry env use python3
	@if [ ! -d "$(VENV_NAME)" ]; then \
		echo "Creating new virtual environment..."; \
		poetry install --with dev; \
	else \
		echo "Virtual environment exists, installing dependencies..."; \
		poetry install --with dev; \
	fi
	@echo "Dependencies installed successfully!"
	@echo "Virtual environment location: $(VENV_NAME)/"

# Setup development environment
setup: install
	@echo "Installing pre-commit hooks..."
	poetry run pre-commit install
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env file created. Please edit it with your credentials."; \
	else \
		echo ".env file already exists."; \
	fi
	@echo "Setup complete!"

# Full development setup from scratch
dev: clean setup
	@echo "Running initial code formatting..."
	@poetry run black . || true
	@echo "Running initial linting..."
	@poetry run ruff check . --fix || true
	@echo "Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env with your Telegram credentials"
	@echo "2. Run 'make run' to start the bot"

# Clean up environment
clean:
	@echo "Cleaning up..."
	rm -rf $(VENV_NAME)
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf __pycache__
	rm -rf yt_summarize_bot/__pycache__
	rm -rf yt_summarize_bot.egg-info
	rm -rf dist
	rm -rf build
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "Cleanup complete!"

# Run tests
test:
	@echo "Running tests..."
	poetry run pytest -v

# Run linting
lint:
	@echo "Running linting..."
	poetry run ruff check .

# Format code
format:
	@echo "Formatting code..."
	poetry run black .
	poetry run ruff check . --fix

# Type checking
typecheck:
	@echo "Running type checking..."
	poetry run mypy yt_summarize_bot

# Run all pre-commit hooks
precommit:
	@echo "Running pre-commit hooks..."
	poetry run pre-commit run --all-files

# Run the bot locally
run:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "Starting bot..."
	poetry run python -m yt_summarize_bot

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker compose build

# Run with docker-compose
docker-run:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "Starting services with docker-compose..."
	docker compose up -d
	@echo "Services started. View logs with: docker compose logs -f"

# Stop docker services
docker-stop:
	@echo "Stopping docker services..."
	docker compose down

# Show docker logs
docker-logs:
	docker compose logs -f bot

# Update dependencies
update:
	@echo "Updating dependencies..."
	poetry update
	poetry run pre-commit autoupdate

# Build package
build:
	@echo "Building package..."
	poetry build

# Install locally in editable mode
install-local:
	@echo "Installing package in editable mode..."
	pip install -e .

# Force recreate virtual environment
recreate-env: check-poetry
	@echo "Removing existing virtual environment..."
	@poetry env remove python 2>/dev/null || true
	@rm -rf $(VENV_NAME)
	@echo "Configuring Poetry for in-project virtual environment..."
	poetry config virtualenvs.in-project true
	@echo "Creating new virtual environment..."
	poetry env use python$(PYTHON_VERSION) || poetry env use python3
	poetry install --with dev
	@echo "Virtual environment recreated: $(VENV_NAME)/"

.DEFAULT_GOAL := help
