"""Unit tests for YouTube transcript fetching."""

from unittest.mock import MagicMock, patch

import pytest
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

from yt_summarize_bot.main import get_youtube_transcript


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
async def test_get_transcript_with_special_characters():
    """Test transcript fetching with special characters."""
    mock_transcript = [
        {"text": "Hello, world!", "start": 0.0, "duration": 1.0},
        {"text": "It's a test & demo", "start": 1.0, "duration": 1.0},
        {"text": "With 'quotes' and \"more\"", "start": 2.0, "duration": 1.0},
    ]

    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.return_value = mock_transcript

        result = await get_youtube_transcript("test_video_id")

        assert result == "Hello, world! It's a test & demo With 'quotes' and \"more\""


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
async def test_get_transcript_multiple_languages_fallback():
    """Test fallback through multiple languages."""
    mock_transcript_list = MagicMock()

    # First transcript (e.g., French) fails
    mock_transcript_fr = MagicMock()
    mock_transcript_fr.fetch.side_effect = Exception("Failed to fetch French")

    # Second transcript (e.g., Spanish) succeeds
    mock_transcript_es = MagicMock()
    mock_transcript_es.fetch.return_value = [
        {"text": "Hola", "start": 0.0, "duration": 1.0},
        {"text": "mundo", "start": 1.0, "duration": 1.0},
    ]

    # Make the mock iterable with two transcripts
    mock_transcript_list.__iter__ = MagicMock(
        return_value=iter([mock_transcript_fr, mock_transcript_es])
    )

    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        # English not found
        mock_api.get_transcript.side_effect = NoTranscriptFound(
            "test_video_id", ["en"], {"en": "English"}
        )
        # list_transcripts returns our mock
        mock_api.list_transcripts.return_value = mock_transcript_list

        result = await get_youtube_transcript("test_video_id")

        assert result == "Hola mundo"


@pytest.mark.asyncio
async def test_get_transcript_generic_exception():
    """Test handling of generic exceptions during transcript fetch."""
    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.side_effect = Exception("Network error")

        result = await get_youtube_transcript("test_video_id")

        assert result is None


@pytest.mark.asyncio
async def test_get_transcript_timeout_exception():
    """Test handling of timeout exceptions during transcript fetch."""
    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.side_effect = TimeoutError("Request timed out")

        result = await get_youtube_transcript("test_video_id")

        assert result is None


@pytest.mark.asyncio
async def test_get_transcript_connection_error():
    """Test handling of connection errors during transcript fetch."""
    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.side_effect = ConnectionError("Failed to connect")

        result = await get_youtube_transcript("test_video_id")

        assert result is None


@pytest.mark.asyncio
async def test_get_transcript_long_content():
    """Test handling of very long transcripts."""
    # Create a transcript with 1000 segments
    mock_transcript = [
        {"text": f"Segment {i}", "start": float(i), "duration": 1.0} for i in range(1000)
    ]

    with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
        mock_api.get_transcript.return_value = mock_transcript

        result = await get_youtube_transcript("test_video_id")

        assert result is not None
        assert len(result) > 5000  # Should be quite long
        assert "Segment 0" in result
        assert "Segment 999" in result


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
