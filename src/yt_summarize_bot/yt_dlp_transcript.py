"""YouTube transcript extraction using yt-dlp as a fallback method."""

import asyncio
import logging
import re

import requests
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

log = logging.getLogger(__name__)

# Supported subtitle languages in order of preference
SUBTITLE_LANGUAGES = ["en", "en-US", "en-GB", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]


def get_yt_dlp_options() -> dict:
    """Get yt-dlp options optimized for transcript extraction."""
    from yt_summarize_bot.config import YouTube

    options = {
        "skip_download": True,
        "writesubtitles": False,  # Don't write to disk
        "writeautomaticsub": False,  # Don't write to disk
        "subtitleslangs": SUBTITLE_LANGUAGES,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        # Enhanced anti-bot detection measures
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        # Additional options to help with extraction
        "extractor_args": {
            "youtube": {
                "skip": ["hls", "dash"],  # Skip livestream formats
                "player_client": ["android", "web"],  # Try multiple clients
            }
        },
    }

    # Add cookie configuration if available
    if YouTube.COOKIES_FROM_BROWSER:
        options["cookiesfrombrowser"] = (YouTube.COOKIES_FROM_BROWSER, None, None, None)
        log.info("Using cookies from browser: %s", YouTube.COOKIES_FROM_BROWSER)
    elif YouTube.COOKIEFILE:
        options["cookiefile"] = YouTube.COOKIEFILE
        log.info("Using cookie file: %s", YouTube.COOKIEFILE)

    return options


def fetch_subtitle_from_url(url: str, timeout: int = 10) -> str | None:
    """Fetch subtitle content from a URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        log.debug("Failed to fetch subtitle from URL %s: %s", url, e)
        return None


def clean_subtitle_text(text: str) -> str:
    """Clean subtitle text by removing timestamps and formatting."""
    if not text:
        return ""

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip WebVTT headers and metadata
        if line.startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:")):
            continue

        # Skip timestamp lines (e.g., "00:00:00.000 --> 00:00:05.000")
        if "-->" in line:
            continue

        # Skip lines that are just numbers (subtitle indices)
        if line.isdigit():
            continue

        # Skip position/alignment tags
        if line.startswith(("align:", "position:", "line:", "size:")):
            continue

        # Remove HTML/XML tags
        line = re.sub(r"<[^>]+>", "", line)

        # Remove speaker tags like [Music] or [Applause]
        line = re.sub(r"\[.*?\]", "", line)

        # Only add non-empty lines after cleaning
        if line:
            cleaned_lines.append(line)

    # Join lines with spaces, removing duplicates
    result = " ".join(cleaned_lines)

    # Clean up multiple spaces
    result = re.sub(r"\s+", " ", result)

    return result.strip()


def extract_subtitle_for_language(
    subtitles: dict, automatic_captions: dict, lang: str
) -> str | None:
    """Try to extract subtitle text for a specific language."""
    # Try manual subtitles first
    if lang in subtitles and subtitles[lang]:
        for subtitle_info in subtitles[lang]:
            if "url" in subtitle_info:
                text = fetch_subtitle_from_url(subtitle_info["url"])
                if text:
                    return clean_subtitle_text(text)

    # Fall back to automatic captions
    if lang in automatic_captions and automatic_captions[lang]:
        for caption_info in automatic_captions[lang]:
            if "url" in caption_info:
                text = fetch_subtitle_from_url(caption_info["url"])
                if text:
                    return clean_subtitle_text(text)

    return None


async def get_transcript_with_yt_dlp(video_url: str) -> str | None:
    """
    Extract transcript from a YouTube video using yt-dlp.

    This is a more robust fallback method when youtube-transcript-api fails.

    Args:
        video_url: Full YouTube URL or video ID

    Returns:
        Transcript text if available, None otherwise
    """
    # Handle both full URLs and video IDs
    if not video_url.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_url}"

    log.info("Attempting to extract transcript with yt-dlp for: %s", video_url)

    ydl_opts = get_yt_dlp_options()
    loop = asyncio.get_event_loop()

    def extract_with_yt_dlp():
        """Synchronous function to run yt-dlp extraction."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video information without downloading
                info = ydl.extract_info(video_url, download=False)

                if not info:
                    log.warning("No video information extracted")
                    return None

                # Get available subtitles and automatic captions
                subtitles = info.get("subtitles", {})
                automatic_captions = info.get("automatic_captions", {})

                log.debug("Available manual subtitles: %s", list(subtitles.keys()))
                log.debug("Available automatic captions: %s", list(automatic_captions.keys()))

                # Try to get subtitles in preferred language order
                for lang in SUBTITLE_LANGUAGES:
                    transcript = extract_subtitle_for_language(subtitles, automatic_captions, lang)
                    if transcript:
                        log.info("Successfully extracted transcript in language: %s", lang)
                        return transcript

                # Try any available language if preferred ones not found
                all_langs = set(list(subtitles.keys()) + list(automatic_captions.keys()))
                for lang in all_langs:
                    if lang not in SUBTITLE_LANGUAGES:
                        transcript = extract_subtitle_for_language(
                            subtitles, automatic_captions, lang
                        )
                        if transcript:
                            log.info(
                                "Successfully extracted transcript in fallback language: %s", lang
                            )
                            return transcript

                log.warning("No transcripts found in any language")
                return None

        except ExtractorError as e:
            log.warning("YouTube extractor error: %s", str(e))
            return None
        except DownloadError as e:
            log.warning("Download error: %s", str(e))
            return None
        except Exception as e:
            log.error("Unexpected error during yt-dlp extraction: %s", str(e))
            return None

    try:
        # Run the synchronous extraction in an executor
        transcript = await loop.run_in_executor(None, extract_with_yt_dlp)
        return transcript  # type: ignore[no-any-return]
    except Exception as e:
        log.error("Failed to run yt-dlp extraction: %s", str(e))
        return None


async def get_video_info(video_url: str) -> dict | None:
    """
    Get video metadata using yt-dlp.

    Args:
        video_url: Full YouTube URL or video ID

    Returns:
        Dictionary with video metadata if successful, None otherwise
    """
    if not video_url.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_url}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    loop = asyncio.get_event_loop()

    def extract_info():
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "channel": info.get("channel", "Unknown"),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "description": info.get("description", ""),
                    "upload_date": info.get("upload_date", ""),
                    "has_subtitles": bool(info.get("subtitles")),
                    "has_auto_captions": bool(info.get("automatic_captions")),
                }
        except Exception as e:
            log.error("Failed to extract video info: %s", str(e))
            return None

    try:
        return await loop.run_in_executor(None, extract_info)
    except Exception as e:
        log.error("Failed to run video info extraction: %s", str(e))
        return None
