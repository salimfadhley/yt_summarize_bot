import asyncio
import base64
import json
import logging
import os
from pathlib import Path

import aiohttp
import requests
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp.utils import DownloadError, ExtractorError

from yt_summarize_bot.config import Ai, Telegram
from yt_summarize_bot.constants import SUBTITLE_LANGUAGES
from yt_summarize_bot.database import db
from yt_summarize_bot.exceptions import (
    CaptionExtractionError,
    MissingAudioFileError,
    SummarizationError,
    TranscriptionError,
    UnsupportedAudioFormatError,
)

log = logging.getLogger(__name__)


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


def _get_subtitle_for_language(subtitles: dict, automatic_captions: dict, lang: str) -> str | None:
    """Try to fetch subtitles for a specific language."""
    try:
        if lang in subtitles:
            sub_url = subtitles[lang][0]["url"]
            response = requests.get(sub_url, timeout=10)
            response.raise_for_status()
            return response.text
        elif lang in automatic_captions:
            sub_url = automatic_captions[lang][0]["url"]
            response = requests.get(sub_url, timeout=10)
            response.raise_for_status()
            return response.text
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        log.debug("Failed to fetch subtitles for language %s: %s", lang, e)
    return None


def load_system_prompt() -> str:
    """Load the system prompt from the system_prompt.txt file."""
    # Locate the file relative to this module
    system_prompt_path = Path(__file__).parent.parent / "system_prompt.txt"

    with system_prompt_path.open("r", encoding="utf-8") as f:
        return f.read().strip()


try:
    bot = Bot(
        token=Telegram.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2)
    )
except Exception as e:
    if "Token is invalid" in str(e) or "TokenValidationError" in str(e):
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
        raise

dp = Dispatcher()


def encode_audio_base64(audio_path: str) -> str:
    try:
        with open(audio_path, "rb") as audio_file:
            return base64.b64encode(audio_file.read()).decode("utf-8")
    except FileNotFoundError as e:
        log.error("Audio file not found at %s", audio_path)
        raise MissingAudioFileError(f"Audio file not found: {audio_path}") from e


def transcribe_audio_sync(audio_path: str, question: str = "Transcribe this audio") -> str:
    url = "https://text.pollinations.ai/openai"
    headers = {"Content-Type": "application/json"}

    base64_audio = encode_audio_base64(audio_path)

    audio_format = audio_path.split(".")[-1].lower()
    supported_formats = ["mp3", "wav"]
    if audio_format not in supported_formats:
        log.warning(
            "Potentially unsupported audio format '%s'. Only %s are officially supported.",
            audio_format,
            ", ".join(supported_formats),
        )
        raise UnsupportedAudioFormatError(
            f"Unsupported audio format: {audio_format}. Supported formats: {', '.join(supported_formats)}"
        )

    payload = {
        "model": "openai-audio",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": base64_audio, "format": audio_format},
                    },
                ],
            }
        ],
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        transcription = result.get("choices", [{}])[0].get("message", {}).get("content")
        if not transcription:
            raise TranscriptionError("Empty transcription response from API")
        return str(transcription)
    except requests.exceptions.RequestException as e:
        log.error("HTTP request failed during audio transcription: %s", e)
        raise TranscriptionError(f"HTTP request failed: {e}") from e
    except json.JSONDecodeError as e:
        log.error("Failed to parse JSON response during audio transcription: %s", e)
        raise TranscriptionError(f"Invalid JSON response: {e}") from e
    except (KeyError, IndexError) as e:
        log.error("Unexpected response format during audio transcription: %s", e)
        raise TranscriptionError(f"Unexpected response format: {e}") from e


async def extract_youtube_transcript(youtube_url: str) -> str:
    try:
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": SUBTITLE_LANGUAGES,
            "outtmpl": "temp_sub.%(ext)s",
            # Add headers to avoid bot detection
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        }

        loop = asyncio.get_event_loop()

        def get_captions_with_ytdlp():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)

                subtitles = info.get("subtitles", {})
                automatic_captions = info.get("automatic_captions", {})

                for lang in SUBTITLE_LANGUAGES:
                    subtitle_text = _get_subtitle_for_language(subtitles, automatic_captions, lang)
                    if subtitle_text:
                        return subtitle_text

                raise CaptionExtractionError("No captions found in any supported language")

        try:
            captions = await loop.run_in_executor(None, get_captions_with_ytdlp)
            lines = captions.split("\n")
            text_lines = [
                line.strip()
                for line in lines
                if line.strip()
                and not line.startswith(("WEBVTT", "NOTE", "STYLE"))
                and "-->" not in line
                and not line.isdigit()
            ]
            return " ".join(text_lines)
        except CaptionExtractionError:
            log.info("No captions available, falling back to audio transcription")
            return await download_audio_and_transcribe(youtube_url)

    except (DownloadError, ExtractorError) as e:
        log.warning("YouTube-DL error during caption extraction: %s", e)
        return await download_audio_and_transcribe(youtube_url)
    except OSError as e:
        log.error("File system error during caption extraction: %s", e)
        return await download_audio_and_transcribe(youtube_url)
    except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
        log.error("Network error during caption extraction: %s", e)
        return await download_audio_and_transcribe(youtube_url)
    except (ValueError, TypeError, KeyError, IndexError) as e:
        log.error("Data processing error during caption extraction: %s", e)
        return await download_audio_and_transcribe(youtube_url)


async def download_audio_and_transcribe(youtube_url: str) -> str:
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }
            ],
            "outtmpl": "temp_audio.%(ext)s",
            "keepvideo": False,
            # Add headers to avoid bot detection
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        }

        loop = asyncio.get_event_loop()

        def download_with_ytdlp():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                return ydl.prepare_filename(info).replace(".webm", ".wav").replace(".m4a", ".wav")

        wav_path = await loop.run_in_executor(None, download_with_ytdlp)

        try:
            transcription = await loop.run_in_executor(None, transcribe_audio_sync, wav_path)
            return str(transcription)
        except (TranscriptionError, UnsupportedAudioFormatError, MissingAudioFileError) as e:
            log.error("Audio transcription failed: %s", e)
            return f"Audio transcription failed: {str(e)}"
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
    except (DownloadError, ExtractorError) as e:
        log.error("YouTube-DL error during audio download: %s", e)
        return f"YouTube download error: {str(e)}"
    except OSError as e:
        log.error("File system error during audio processing: %s", e)
        return f"File system error: {str(e)}"
    except (ConnectionError, TimeoutError) as e:
        log.error("Network error during audio transcription: %s", e)
        return f"Network error during audio transcription: {str(e)}"
    except (ValueError, TypeError, RuntimeError) as e:
        log.error("Processing error during audio transcription: %s", e)
        return f"Audio transcription error: {str(e)}"


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
        status_msg = await safe_send_message(message, "Reading the video...")
        transcript_text = await extract_youtube_transcript(url)
        if (
            "captions xml" in transcript_text.lower()
            or "no transcript" in transcript_text.lower()
            or "error" in transcript_text.lower()
            or "failed" in transcript_text.lower()
        ):
            log.warning("Failed to extract transcript for URL %s: %s", url, transcript_text)
            await safe_edit_message(status_msg, transcript_text)
        else:
            log.info("Successfully extracted transcript for URL %s, generating summary", url)
            try:
                summary = await get_llm_response(transcript_text)
                log.info("Successfully generated summary for URL %s", url)
                await safe_edit_message(status_msg, summary)
            except SummarizationError as e:
                log.warning("Failed to generate summary for URL %s: %s", url, e)
                await safe_edit_message(status_msg, f"Could not generate summary: {str(e)}")
    else:
        log.debug("Non-YouTube URL received from user %s: %s", user_id, url)
        await message.answer("Please send a valid YouTube link.")


async def main() -> None:
    log.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
