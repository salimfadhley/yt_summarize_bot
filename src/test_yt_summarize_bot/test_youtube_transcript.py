"""Unit tests for YouTube transcript extraction."""

from unittest.mock import MagicMock, patch

import pytest

from yt_summarize_bot.main import get_video_id, get_youtube_transcript


class TestVideoIdExtraction:
    """Test video ID extraction from various YouTube URL formats."""

    def test_standard_youtube_url(self):
        """Test extraction from standard youtube.com URL."""
        url = "https://www.youtube.com/watch?v=pqoBgMoWH18"
        assert get_video_id(url) == "pqoBgMoWH18"

    def test_youtube_url_with_timestamp(self):
        """Test extraction from YouTube URL with timestamp."""
        url = "https://www.youtube.com/watch?v=pqoBgMoWH18&t=63s"
        assert get_video_id(url) == "pqoBgMoWH18"

    def test_short_youtube_url(self):
        """Test extraction from youtu.be short URL."""
        url = "https://youtu.be/pqoBgMoWH18"
        assert get_video_id(url) == "pqoBgMoWH18"

    def test_short_url_with_params(self):
        """Test extraction from short URL with parameters."""
        url = "https://youtu.be/pqoBgMoWH18?t=63"
        assert get_video_id(url) == "pqoBgMoWH18"

    def test_invalid_url(self):
        """Test that invalid URLs return None."""
        url = "https://example.com/video"
        assert get_video_id(url) is None

    def test_malformed_url(self):
        """Test that malformed URLs return None."""
        url = "not-a-url"
        assert get_video_id(url) is None


class TestYouTubeTranscript:
    """Test YouTube transcript fetching."""

    @pytest.mark.asyncio
    async def test_get_transcript_success(self):
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
    async def test_get_transcript_no_transcript_found(self):
        """Test handling when no transcript is found."""
        from youtube_transcript_api import NoTranscriptFound

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
    async def test_get_transcript_disabled(self):
        """Test handling when transcripts are disabled."""
        from youtube_transcript_api import TranscriptsDisabled

        with patch("yt_summarize_bot.main.YouTubeTranscriptApi") as mock_api:
            mock_api.get_transcript.side_effect = TranscriptsDisabled("test_video_id")

            result = await get_youtube_transcript("test_video_id")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_transcript_fallback_language(self):
        """Test fallback to available language when English not found."""
        from youtube_transcript_api import NoTranscriptFound

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
    @pytest.mark.integration
    async def test_real_video_transcript(self):
        """Integration test with real YouTube video - only run manually."""
        # This test actually calls YouTube API - mark as integration test
        # Run with: pytest -m integration
        # Using a popular tech video that should have transcripts
        video_id = "dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up (reliable test video)

        result = await get_youtube_transcript(video_id)

        # We can't assert exact content as it may change, but we can check:
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 100  # Should have substantial content
        # Check for some expected words from the famous song
        assert "never" in result.lower() or "gonna" in result.lower()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
