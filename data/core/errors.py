"""Typed adapter errors. The agent gets `ErrorInfo` (see schemas), never a raw exception."""
from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    TIMEOUT = "timeout"
    NETWORK = "network"
    RATE_LIMITED = "rate_limited"
    AUTH = "auth"
    MISSING_CREDENTIALS = "missing_credentials"
    NOT_FOUND = "not_found"
    BAD_REQUEST = "bad_request"
    SERVER = "server_error"
    BAD_RESPONSE = "bad_response"
    SIMULATED_OUTAGE = "simulated_outage"
    UNKNOWN = "unknown"


class AdapterError(Exception):
    def __init__(
        self,
        type: ErrorType,
        message: str,
        *,
        http_status: Optional[int] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.type = type
        self.message = message
        self.http_status = http_status
        self.retryable = retryable

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.type.value}] {self.message}"


class NoCoverage(Exception):
    """The API works but has nothing for this place (e.g. no OpenAQ station in range).
    This is *not* an outage and *not* 'clean air' — it's absence of coverage."""
