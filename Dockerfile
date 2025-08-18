# Use Python 3.12 slim image
FROM python:3.12-slim as yt_summarize_bot_base

# Install system dependencies for audio processing and ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.5

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create virtual environment in Docker
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --only main

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser


from yt_summarize_bot_base as yt_summarize_bot

# Run the bot as a module
CMD ["python", "-m", "yt_summarize_bot"]

FROM yt_summarize_bot_base as yt_summarize_bot_dev

# Switch back to root to install dev dependencies
USER root

# Install development dependencies (black, ruff, mypy, pytest)
RUN poetry install --no-interaction --no-ansi --with dev

# Switch back to botuser
USER botuser

# Run the bot as a module (same as production but with dev tools available)
CMD ["python", "-m", "yt_summarize_bot"]