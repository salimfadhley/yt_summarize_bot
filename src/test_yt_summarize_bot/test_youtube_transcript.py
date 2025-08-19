"""Unit tests for YouTube transcript extraction."""

from unittest.mock import MagicMock, patch

import pytest
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

from yt_summarize_bot.main import get_video_id, get_youtube_transcript


# Video ID extraction tests
def test_standard_youtube_url():
    """Test extraction from standard youtube.com URL."""
    url = "https://www.youtube.com/watch?v=pqoBgMoWH18"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_youtube_url_with_timestamp():
    """Test extraction from YouTube URL with timestamp."""
    url = "https://www.youtube.com/watch?v=pqoBgMoWH18&t=63s"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_short_youtube_url():
    """Test extraction from youtu.be short URL."""
    url = "https://youtu.be/pqoBgMoWH18"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_short_url_with_params():
    """Test extraction from short URL with parameters."""
    url = "https://youtu.be/pqoBgMoWH18?t=63"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_invalid_url():
    """Test that invalid URLs return None."""
    url = "https://example.com/video"
    assert get_video_id(url) is None


def test_malformed_url():
    """Test that malformed URLs return None."""
    url = "not-a-url"
    assert get_video_id(url) is None


def test_empty_url():
    """Test that empty string returns None."""
    assert get_video_id("") is None


def test_none_url():
    """Test that None input is handled gracefully."""
    assert get_video_id(None) is None  # type: ignore


# YouTube transcript fetching tests
@pytest.mark.asyncio
async def test_get_transcript_success():
    """Test successful transcript fetching."""
    mock_transcript = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "World", "start": 1.0, "duration": 1.0},
        {"text": "This is a test", "start": 2.0, "duration": 2.0},
    ]

    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.return_value = mock_transcript

        result = await get_youtube_transcript("test_video_id")

        assert result == "Hello World This is a test"
        mock_api.get_transcript.assert_called_once_with("test_video_id")


@pytest.mark.asyncio
async def test_get_transcript_no_transcript_found():
    """Test handling when no transcript is found."""
    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.side_effect = NoTranscriptFound(
            "test_video_id", ["en"], {"en": "English"}
        )
        mock_api.list_transcripts.side_effect = NoTranscriptFound(
            "test_video_id", ["en"], {"en": "English"}
        )

        result = await get_youtube_transcript("test_video_id")

        assert result is None


@pytest.mark.asyncio
async def test_get_transcript_disabled():
    """Test handling when transcripts are disabled."""
    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.side_effect = TranscriptsDisabled("test_video_id")

        result = await get_youtube_transcript("test_video_id")

        assert result is None


@pytest.mark.asyncio
async def test_get_transcript_fallback_language():
    """Test fallback to available language when English not found."""
    mock_transcript_list = MagicMock()
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [
        {"text": "Bonjour", "start": 0.0, "duration": 1.0},
        {"text": "le monde", "start": 1.0, "duration": 1.0},
    ]

    # Make the mock iterable
    mock_transcript_list.__iter__ = MagicMock(return_value=iter([mock_transcript]))

    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        # First call raises NoTranscriptFound
        mock_api.get_transcript.side_effect = NoTranscriptFound(
            "test_video_id", ["en"], {"en": "English"}
        )
        # list_transcripts returns our mock
        mock_api.list_transcripts.return_value = mock_transcript_list

        result = await get_youtube_transcript("test_video_id")

        assert result == "Bonjour le monde"


@pytest.mark.asyncio
async def test_get_transcript_empty_text():
    """Test handling of transcript entries with empty text."""
    mock_transcript = [
        {"text": "Hello", "start": 0.0, "duration": 1.0},
        {"text": "", "start": 1.0, "duration": 1.0},
        {"text": "World", "start": 2.0, "duration": 1.0},
    ]

    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.return_value = mock_transcript

        result = await get_youtube_transcript("test_video_id")

        assert result == "Hello  World"  # Empty text still adds a space


@pytest.mark.asyncio
async def test_get_transcript_generic_exception():
    """Test handling of generic exceptions during transcript fetch."""
    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.side_effect = Exception("Network error")

        result = await get_youtube_transcript("test_video_id")

        assert result is None


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skip(reason="Integration test - run manually with 'pytest -m integration'")
async def test_real_video_transcript():
    """Integration test with real YouTube video - only run manually."""
    # This test actually calls YouTube API - mark as integration test
    # Run with: pytest -m integration -k test_real_video_transcript
    # Using a tech talk that should have transcripts
    video_id = "rRbY3TMUcgQ"  # A tech conference talk (more reliable for transcripts)

    result = await get_youtube_transcript(video_id)

    # We can't assert exact content as it may change, but we can check:
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 100  # Should have substantial content


# Parametrized tests for better coverage
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=abc123def45", "abc123def45"),
        ("https://youtu.be/xyz789ghi01", "xyz789ghi01"),
        ("https://www.youtube.com/watch?v=test1234567&feature=share", "test1234567"),
        ("https://m.youtube.com/watch?v=mobile12345", "mobile12345"),
        ("https://youtube.com/watch?v=nowww12345", "nowww12345"),
        ("http://youtu.be/http1234567", "http1234567"),
    ],
)
def test_video_id_extraction_parametrized(url, expected):
    """Test video ID extraction with various URL formats."""
    assert get_video_id(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/123456789",
        "https://dailymotion.com/video/x123456",
        "https://www.twitch.tv/videos/123456789",
        "not-a-url-at-all",
        "",
    ],
)
def test_invalid_urls_parametrized(url):
    """Test that non-YouTube URLs return None."""
    assert get_video_id(url) is None
