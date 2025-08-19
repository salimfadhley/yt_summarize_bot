import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

from yt_summarize_bot.config import Ai, Telegram
from yt_summarize_bot.database import db
from yt_summarize_bot.exceptions import SummarizationError

log = logging.getLogger(__name__)


def get_video_id(url: str | None) -> str | None:
    """Extract YouTube video ID from URL."""
    if not url:
        return None

    try:
        # Only process YouTube URLs
        if "youtube.com" not in url and "youtu.be" not in url:
            return None

        # Handle different YouTube URL formats
        if "youtube.com" in url:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            return query_params.get("v", [None])[0]
        elif "youtu.be" in url:
            parsed = urlparse(url)
            path = parsed.path[1:] if parsed.path else ""
            return path.split("?")[0] if path else None
        else:
            return None
    except Exception as e:
        log.error("Error extracting video ID from URL %s: %s", url, e)
        return None


async def get_youtube_transcript(video_id: str) -> str | None:
    """Fetch YouTube video transcript."""
    try:
        loop = asyncio.get_event_loop()

        def fetch_transcript():
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                # Join all transcript text parts into a single string
                transcript = " ".join([item["text"] for item in transcript_list])
                return transcript
            except NoTranscriptFound:
                # Try to get transcript in any available language
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                for transcript in transcript_list:
                    try:
                        fetched = transcript.fetch()
                        return " ".join([item["text"] for item in fetched])
                    except Exception:
                        continue
                return None

        transcript = await loop.run_in_executor(None, fetch_transcript)
        return transcript  # type: ignore[no-any-return]
    except NoTranscriptFound:
        log.warning("No transcript found for video ID '%s'", video_id)
        return None
    except TranscriptsDisabled:
        log.warning("Transcripts are disabled for video ID '%s'", video_id)
        return None
    except Exception as e:
        log.error("Error fetching transcript for video ID '%s': %s", video_id, e)
        return None


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    # Characters that need escaping in Telegram MarkdownV2
    special_chars = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]

    for char in special_chars:
        text = text.replace(char, f"\\{char}")

    return text


async def safe_send_message(message: types.Message, text: str) -> types.Message:
    """Safely send a message, falling back to plain text if MarkdownV2 parsing fails."""
    try:
        result = await message.answer(text, parse_mode=ParseMode.MARKDOWN_V2)
        return result
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            log.warning("MarkdownV2 parsing failed, sending as escaped text: %s", e)
            escaped_text = escape_markdown_v2(text)
            try:
                result = await message.answer(escaped_text, parse_mode=ParseMode.MARKDOWN_V2)
                return result
            except TelegramBadRequest:
                log.warning("Even escaped MarkdownV2 failed, sending as plain text")
                result = await message.answer(text, parse_mode=None)
                return result
        else:
            raise


async def safe_edit_message(message: types.Message, text: str) -> bool:
    """Safely edit a message, falling back to plain text if MarkdownV2 parsing fails."""
    try:
        await message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)
        return True
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e).lower():
            log.warning("MarkdownV2 parsing failed, editing as escaped text: %s", e)
            escaped_text = escape_markdown_v2(text)
            try:
                await message.edit_text(escaped_text, parse_mode=ParseMode.MARKDOWN_V2)
                return True
            except TelegramBadRequest:
                log.warning("Even escaped MarkdownV2 failed, editing as plain text")
                await message.edit_text(text, parse_mode=None)
                return True
        else:
            raise


def load_system_prompt() -> str:
    """Load the system prompt from the system_prompt.txt file."""
    # Locate the file in the same directory as this module
    system_prompt_path = Path(__file__).parent / "system_prompt.txt"

    with system_prompt_path.open("r", encoding="utf-8") as f:
        return f.read().strip()


try:
    bot = Bot(
        token=Telegram.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2)
    )
except (ValueError, RuntimeError) as e:
    # Handle specific Telegram bot initialization errors
    if "Token is invalid" in str(e) or "TokenValidationError" in str(e) or "401" in str(e):
        print("ERROR: Invalid Telegram Bot Token")
        print()
        print("How to get a valid Telegram Bot Token:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Start a chat with @BotFather")
        print("3. Send the command: /newbot")
        print("4. Follow the prompts to create your bot")
        print("5. Copy the token @BotFather provides")
        print("6. Add it to your .env file as: BOT_TOKEN=your_token_here")
        print()
        print(
            "For more details, see: https://core.telegram.org/bots/tutorial#obtain-your-bot-token"
        )
        exit(1)
    else:
        # Re-raise if it's a different ValueError/RuntimeError
        raise
except (ConnectionError, TimeoutError) as e:
    print("ERROR: Network connection failed while initializing Telegram bot")
    print(f"Details: {e}")
    print("Please check your internet connection and try again.")
    exit(1)

dp = Dispatcher()


async def get_gemini_video_summary(youtube_url: str) -> str:
    """Get video summary using transcript extraction + Gemini."""
    system_prompt = load_system_prompt()

    # Only try Gemini if we have an API key configured
    if not Ai.API_KEY:
        raise SummarizationError("Gemini API key not configured")

    # Extract video ID from URL
    video_id = get_video_id(youtube_url)
    if not video_id:
        raise SummarizationError("Could not extract video ID from URL")

    # Get transcript
    log.info("Fetching transcript for video ID: %s", video_id)
    transcript = await get_youtube_transcript(video_id)
    if not transcript:
        raise SummarizationError("No transcript available for this video")

    log.info("Transcript fetched, length: %d characters", len(transcript))

    # Prepare prompt with transcript
    prompt = f"{system_prompt}\n\nPlease provide a comprehensive summary of the following YouTube video transcript:\n\n{transcript}"

    url = Ai.API_URL
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 2000,
            "temperature": 0.7,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": Ai.API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                if "candidates" in data and data["candidates"]:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if parts and "text" in parts[0]:
                            content = parts[0]["text"]
                            if not content:
                                raise SummarizationError("Empty response from Gemini API")
                            return str(content)
                raise SummarizationError("No valid response format found in Gemini API response")
    except aiohttp.ClientError as e:
        log.error("HTTP client error during Gemini request: %s", e)
        raise SummarizationError(f"HTTP client error: {e}") from e
    except TimeoutError as e:
        log.error("Timeout during Gemini request: %s", e)
        raise SummarizationError(f"Request timeout: {e}") from e
    except json.JSONDecodeError as e:
        log.error("Failed to parse JSON response from Gemini: %s", e)
        raise SummarizationError(f"Invalid JSON response: {e}") from e
    except (KeyError, IndexError) as e:
        log.error("Unexpected response format from Gemini: %s", e)
        raise SummarizationError(f"Unexpected response format: {e}") from e


async def get_llm_response(prompt: str) -> str:
    system_prompt = load_system_prompt()

    if Ai.API_KEY:
        url = Ai.API_URL
        payload = {
            "model": Ai.MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1500,
            "temperature": 0.7,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {Ai.API_KEY}",
        }
    else:
        url = "https://text.pollinations.ai/openai"
        payload = {
            "model": "openai",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "seed": 101,
            "temperature": 0.7,
        }
        headers = {"Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    if not content:
                        raise SummarizationError("Empty response from LLM API")
                    return str(content)
                elif "message" in data:
                    content = data["message"]["content"]
                    if not content:
                        raise SummarizationError("Empty response from LLM API")
                    return str(content)
                raise SummarizationError("No valid response format found in LLM API response")
    except aiohttp.ClientError as e:
        log.error("HTTP client error during LLM request: %s", e)
        raise SummarizationError(f"HTTP client error: {e}") from e
    except TimeoutError as e:
        log.error("Timeout during LLM request: %s", e)
        raise SummarizationError(f"Request timeout: {e}") from e
    except json.JSONDecodeError as e:
        log.error("Failed to parse JSON response from LLM: %s", e)
        raise SummarizationError(f"Invalid JSON response: {e}") from e
    except (KeyError, IndexError) as e:
        log.error("Unexpected response format from LLM: %s", e)
        raise SummarizationError(f"Unexpected response format: {e}") from e


@dp.message(Command("start"))
async def start_command(message: types.Message) -> None:
    user_id = message.from_user.id if message.from_user else "unknown"
    log.info("Start command received from user %s", user_id)

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(
            text="View Source Code",
            url="https://github.com/Harshit-shrivastav/YouTube-Summarizer-Bot",
        )
    )
    await message.answer(
        "Send me a YouTube link, and I will summarize that video for you in text format.",
        reply_markup=builder.as_markup(),
    )
    if message.from_user and not await db.is_inserted("users", message.from_user.id):
        await db.insert("users", message.from_user.id)
        log.info("New user registered: %s", message.from_user.id)


@dp.message(Command("users"))
async def users_command(message: types.Message) -> None:
    if not message.from_user or message.from_user.id != Telegram.AUTH_USER_ID:
        return
    try:
        users = len(await db.fetch_all("users"))
        await message.answer(f"Total Users: {users}")
    except (ConnectionError, TimeoutError) as e:
        log.error("Database connection error while fetching user count: %s", e)
        await message.answer("Database connection failed. Please try again later.")
    except (ValueError, TypeError) as e:
        log.error("Data processing error while fetching user count: %s", e)
        await message.answer("Failed to retrieve user count.")


@dp.message(Command("bcast"))
async def bcast_command(message: types.Message) -> None:
    if not message.from_user or message.from_user.id != Telegram.AUTH_USER_ID:
        return
    if not message.reply_to_message:
        await message.answer("Please use `/bcast` as a reply to the message you want to broadcast.")
        return
    msg = message.reply_to_message
    status_msg = await message.answer("Broadcasting...")
    error_count = 0
    users = await db.fetch_all("users")
    for user in users:
        try:
            await bot.copy_message(
                chat_id=int(user), from_chat_id=message.chat.id, message_id=msg.message_id
            )
        except (ValueError, TypeError) as e:
            log.warning("Invalid user ID during broadcast: %s - %s", user, e)
            error_count += 1
        except (ConnectionError, TimeoutError) as e:
            log.warning("Network error sending message to user %s during broadcast: %s", user, e)
            error_count += 1
        except RuntimeError as e:
            log.warning("Bot API error sending message to user %s during broadcast: %s", user, e)
            error_count += 1
    await status_msg.edit_text(f"Broadcasted message with {error_count} errors.")


@dp.message()
async def handle_message(message: types.Message) -> None:
    if not message.text:
        return

    user_id = message.from_user.id if message.from_user else "unknown"
    url = message.text.strip()

    if "youtube.com" in url or "youtu.be" in url:
        log.info("Processing YouTube URL from user %s: %s", user_id, url)
        status_msg = await safe_send_message(message, "Analyzing the video...")

        # Use Gemini for direct YouTube URL processing
        try:
            log.info("Attempting Gemini video processing for URL %s", url)
            summary = await get_gemini_video_summary(url)
            log.info("Successfully generated summary via Gemini for URL %s", url)
            await safe_edit_message(status_msg, summary)
        except SummarizationError as e:
            log.warning("Gemini video processing failed for URL %s: %s", url, e)
            await safe_edit_message(status_msg, f"Could not process video: {str(e)}")
    else:
        log.debug("Non-YouTube URL received from user %s: %s", user_id, url)
        await message.answer("Please send a valid YouTube link.")


async def main() -> None:
    log.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
