"""Error types for the Whisper Security Knowledge Graph API client.

Provides structured error representations for API failures, including
HTTP status code classification, retry eligibility, and RFC 7807
Problem Detail support.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WhisperAPIError:
    """Structured error from the Whisper API.

    Attributes:
        status_code: HTTP status code (0 for connection errors).
        error_type: Classification of the error.
        message: Human-readable error message.
        retryable: Whether the request can be retried.
        raw_response: Original response body if available.
        extra: Additional fields from RFC 7807 responses (e.g., timeoutMs, actualDepth).
    """

    status_code: int
    error_type: str
    message: str
    retryable: bool
    raw_response: str | None = None
    extra: dict[str, Any] | None = None


class WhisperAPIRequestError(Exception):
    """Exception raised for Whisper API errors.

    Attributes:
        error: Structured error details.
    """

    def __init__(self, error: WhisperAPIError) -> None:
        self.error = error
        super().__init__(f"Whisper API error {error.status_code}: {error.message}")
