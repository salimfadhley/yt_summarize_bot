# YouTube Video Summarizer Bot

Welcome to the YouTube Video Summarizer Bot! This bot helps you to get a quick summary of any YouTube video by simply sending a link. It uses advanced AI technologies to transcribe and summarize the content for you.

## Features

- **YouTube Link Handling**: Just send a YouTube link to the bot.
- **Automatic Captions**: If the video has captions, it will use them to generate the summary.
- **Audio Transcription**: If no captions are available, it will download the audio and transcribe it.
- **Text Summarization**: Summarizes the transcribed text using advanced AI models.
- **Easy to Use**: Simple commands to interact with the bot.
- **OpenAI Compatible**: Use any OpenAI Compatible model.

### Free Bot Hosting
If you want free bot hosting, checkout this article:
https://github.com/Harshit-shrivastav/Free-Telegram-bot-hosting
## Quick Start - Local Development

The fastest way to get started with local development is using our automation tools:

```bash
# Clone the repository
git clone https://github.com/Harshit-shrivastav/Youtube-Summarizer-Bot.git
cd Youtube-Summarizer-Bot

# Run automated setup (installs everything you need)
./setup.sh

# Edit your credentials
nano .env  # Add your BOT_TOKEN and AUTH_USER_ID

# Run the bot
make run
```

The `Makefile` provides convenient commands for all common development tasks. Run `make help` to see all available commands.

## Installation

### Prerequisites

1. **Create a Telegram Bot**:
   - Open Telegram and search for [@BotFather](https://t.me/botfather)
   - Send `/newbot` and follow the instructions
   - Save the bot token you receive (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **Get Your Telegram User ID**:
   - Search for [@userinfobot](https://t.me/userinfobot) on Telegram
   - Start a chat and it will show your user ID
   - Save this ID for admin commands

### Using Docker (Recommended)

1. Clone the repository:
    ```bash
    git clone https://github.com/Harshit-shrivastav/Youtube-Summarizer-Bot.git
    cd Youtube-Summarizer-Bot
    ```

2. Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

3. Edit `.env` and add your credentials:
    ```bash
    # Required
    BOT_TOKEN=your_telegram_bot_token_here
    AUTH_USER_ID=your_telegram_user_id_here

    # Optional (uses free service if not provided)
    AI_API_KEY=your_api_key_here
    ```

4. Run with Docker Compose:
    ```bash
    docker compose up -d
    ```

### Understanding .env Files

The `.env` file stores sensitive configuration like API keys and tokens. Here's how it works:

- **`.env.example`** - Template file with placeholder values (committed to git)
- **`.env`** - Your actual configuration with real credentials (ignored by git)
- **Security** - Never commit `.env` to version control as it contains secrets
- **Docker** - Automatically loaded by docker-compose via `env_file: - .env`
- **Local Development** - Loaded by python-dotenv when running locally

The bot will not start without the required values (BOT_TOKEN and AUTH_USER_ID) in your `.env` file.

### Local Development with Makefile

The project includes a `Makefile` that automates common development tasks:

| Command | Description |
|---------|-------------|
| `make dev` | Complete development setup from scratch |
| `make setup` | Install dependencies and pre-commit hooks |
| `make run` | Run the bot locally |
| `make test` | Run all tests |
| `make format` | Format code with black |
| `make lint` | Check code with ruff |
| `make typecheck` | Type check with mypy |
| `make clean` | Remove all cache and build files |
| `make help` | Show all available commands |

#### Quick Setup (Automated)

```bash
# Option 1: Using the setup script (recommended for first-time setup)
./setup.sh

# Option 2: Using Make
make dev
```

#### Manual Setup

1. Install Poetry and dependencies:
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    poetry install
    ```

2. Set up environment variables:
    ```bash
    export BOT_TOKEN='your_telegram_bot_token'  # REQUIRED
    export AUTH_USER_ID='your_telegram_user_id' # REQUIRED
    export AI_API_KEY='google-genai_api_key'     # optional
    export REDIS_HOST='your_redis_host'          # optional
    export REDIS_PORT='your_redis_port'          # optional
    export REDIS_PASSWORD='your_redis_password'  # optional
    ```

3. Run the bot:
    ```bash
    poetry run python -m yt_summarize_bot
    ```
---
> You can get Google-genai API key from here - [GOOGLE_API_KEY](https://aistudio.google.com/apikey?_gl=1*1ikijsu*_ga*MTM2NzM3ODU0MC4xNzQ3NTg3NTEy*_ga_P1DBVKWT6V*czE3NDc3NDg2NjYkbzQkZzEkdDE3NDc3NDg4MjckajQ1JGwwJGgxNDk1NTE1NTI3JGQ1M05kWER0TVBXVkdkS0Q4Zk4zVmJoNnI4Yi1yY3hoM0tn)
---
## Usage

1. Start the bot:

    ```bash
    python3 main.py
    ```

2. Open Telegram and start a chat with your bot.
3. Send the `/start` command to get started.
4. Send any YouTube link to get a summarized text of the video content.

## Contributing

Contributions are welcome! Please fork this repository and submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram client library.
- [Pytube](https://github.com/pytube/pytube) - YouTube video downloader.
- [SpeechRecognition](https://github.com/Uberi/speech_recognition) - Library for performing speech recognition.
- [Gemini AI](https://gemini.google.com/) - GenAI Api for summarization

## Contact

For any queries, reach out at [telegram](https://telegram.me/izharshit).

Enjoy summarizing!

## Follow me
Your follow is like a virtual high-five. Thanks!
- [GitHub](https://github.com/Harshit-shrivastav)
