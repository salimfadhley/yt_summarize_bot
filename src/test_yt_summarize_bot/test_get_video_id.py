"""Unit tests for YouTube video ID extraction."""

import pytest

from yt_summarize_bot.main import get_video_id


def test_standard_youtube_url():
    """Test extraction from standard youtube.com URL."""
    url = "https://www.youtube.com/watch?v=pqoBgMoWH18"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_youtube_url_with_timestamp():
    """Test extraction from YouTube URL with timestamp."""
    url = "https://www.youtube.com/watch?v=pqoBgMoWH18&t=63s"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_youtube_url_with_multiple_params():
    """Test extraction from YouTube URL with multiple parameters."""
    url = "https://www.youtube.com/watch?v=test1234567&feature=share&t=123"
    assert get_video_id(url) == "test1234567"


def test_short_youtube_url():
    """Test extraction from youtu.be short URL."""
    url = "https://youtu.be/pqoBgMoWH18"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_short_url_with_params():
    """Test extraction from short URL with parameters."""
    url = "https://youtu.be/pqoBgMoWH18?t=63"
    assert get_video_id(url) == "pqoBgMoWH18"


def test_mobile_youtube_url():
    """Test extraction from mobile YouTube URL."""
    url = "https://m.youtube.com/watch?v=mobile12345"
    assert get_video_id(url) == "mobile12345"


def test_youtube_url_without_www():
    """Test extraction from YouTube URL without www."""
    url = "https://youtube.com/watch?v=nowww12345"
    assert get_video_id(url) == "nowww12345"


def test_http_youtube_url():
    """Test extraction from HTTP (non-HTTPS) YouTube URL."""
    url = "http://www.youtube.com/watch?v=http1234567"
    assert get_video_id(url) == "http1234567"


def test_http_short_url():
    """Test extraction from HTTP short URL."""
    url = "http://youtu.be/http1234567"
    assert get_video_id(url) == "http1234567"


def test_invalid_url():
    """Test that invalid URLs return None."""
    url = "https://example.com/video"
    assert get_video_id(url) is None


def test_vimeo_url():
    """Test that Vimeo URLs return None."""
    url = "https://vimeo.com/123456789"
    assert get_video_id(url) is None


def test_dailymotion_url():
    """Test that Dailymotion URLs return None."""
    url = "https://dailymotion.com/video/x123456"
    assert get_video_id(url) is None


def test_twitch_url():
    """Test that Twitch URLs return None."""
    url = "https://www.twitch.tv/videos/123456789"
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


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize(
    "url,expected",
    [
        # Standard YouTube URLs
        ("https://www.youtube.com/watch?v=abc123def45", "abc123def45"),
        (
            "https://www.youtube.com/watch?v=xyz789ghi01&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
            "xyz789ghi01",
        ),
        ("https://www.youtube.com/watch?v=test1234567&feature=share", "test1234567"),
        # Short URLs
        ("https://youtu.be/xyz789ghi01", "xyz789ghi01"),
        ("https://youtu.be/short123456?t=42", "short123456"),
        # Mobile URLs
        ("https://m.youtube.com/watch?v=mobile12345", "mobile12345"),
        # Without www
        ("https://youtube.com/watch?v=nowww12345", "nowww12345"),
        # HTTP URLs
        ("http://www.youtube.com/watch?v=http1234567", "http1234567"),
        ("http://youtu.be/http1234567", "http1234567"),
    ],
)
def test_video_id_extraction_parametrized(url, expected):
    """Test video ID extraction with various valid YouTube URL formats."""
    assert get_video_id(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        # Non-YouTube video platforms
        "https://vimeo.com/123456789",
        "https://dailymotion.com/video/x123456",
        "https://www.twitch.tv/videos/123456789",
        "https://www.facebook.com/watch/?v=123456789",
        # Invalid URLs
        "not-a-url-at-all",
        "ftp://example.com/video.mp4",
        "file:///home/user/video.mp4",
        # Empty/None
        "",
        # Random websites
        "https://example.com/watch?v=123456",
        "https://google.com/search?q=youtube",
    ],
)
def test_invalid_urls_parametrized(url):
    """Test that non-YouTube URLs return None."""
    assert get_video_id(url) is None
