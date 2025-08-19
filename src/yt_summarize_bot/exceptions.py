"""Custom exceptions for the YouTube Summarizer Bot."""

import logging

log = logging.getLogger(__name__)


class YTSummarizerBotError(Exception):
    """Base exception for all YouTube Summarizer Bot errors."""

    pass


class MissingConfigurationError(YTSummarizerBotError):
    """Raised when required configuration is missing."""

    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name
        message = f"Missing required configuration: {variable_name}"
        super().__init__(message)
        log.error(message)


class TranscriptionError(YTSummarizerBotError):
    """Raised when audio transcription fails."""

    pass


class YouTubeError(YTSummarizerBotError):
    """Raised when YouTube operations fail."""

    pass


class SummarizationError(YTSummarizerBotError):
    """Raised when text summarization fails."""

    pass


class MissingAudioFileError(YTSummarizerBotError):
    """Raised when an audio file is not found or cannot be accessed."""

    pass


class UnsupportedAudioFormatError(YTSummarizerBotError):
    """Raised when an unsupported audio format is encountered."""

    pass


class CaptionExtractionError(YTSummarizerBotError):
    """Raised when caption extraction fails."""

    pass
