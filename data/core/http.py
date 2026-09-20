"""One place for outbound HTTP: timeouts, limited retries, typed errors, secret redaction."""
from __future__ import annotations

import re
import threading
from typing import Any, Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from data.config import known_secret_values
from data.core.errors import AdapterError, ErrorType

DEFAULT_TIMEOUT: Tuple[float, float] = (5.0, 20.0)  # (connect, read) seconds
USER_AGENT = "TerraWatch/0.1 (environmental investigation agent; hackathon)"

_session: Optional[requests.Session] = None
_lock = threading.Lock()
_KEY_PATTERN = re.compile(r"(?i)\b(api[_-]?key|map[_-]?key|token)=([^&\s]+)")


def redact(text: Any) -> str:
    """Remove API keys from anything that might reach logs, the agent, or the UI."""
    s = str(text)
    for secret in known_secret_values():
        if len(secret) >= 4:
            s = s.replace(secret, "***")
    return _KEY_PATTERN.sub(lambda m: f"{m.group(1)}=***", s)


def _get_session() -> requests.Session:
    global _session
    with _lock:
        if _session is None:
            s = requests.Session()
            # Retry only transient server-side failures. 429 is deliberately NOT retried:
            # waiting on Retry-After would stall the agent; the cache layer handles it instead.
            retry = Retry(
                total=2,
                connect=2,
                read=1,
                backoff_factor=0.4,
                status_forcelist=(500, 502, 503, 504),
                allowed_methods=frozenset(["GET"]),
                raise_on_status=False,
            )
            s.mount("https://", HTTPAdapter(max_retries=retry))
            s.mount("http://", HTTPAdapter(max_retries=retry))
            s.headers.update({"User-Agent": USER_AGENT})
            _session = s
        return _session


def reference_url(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Reproducible, key-free URL to store as `raw_reference`."""
    prepared = requests.Request("GET", url, params=params).prepare()
    return redact(prepared.url)


def _raise_for_status(resp: requests.Response) -> None:
    code = resp.status_code
    if code < 400:
        return
    snippet = redact((resp.text or "")[:200]).replace("\n", " ")
    if code in (401, 403):
        raise AdapterError(ErrorType.AUTH, f"Authentication rejected (HTTP {code}). {snippet}", http_status=code)
    if code == 404:
        raise AdapterError(ErrorType.NOT_FOUND, f"Resource not found (HTTP 404). {snippet}", http_status=code)
    if code == 408:
        raise AdapterError(ErrorType.TIMEOUT, "Upstream request timeout (HTTP 408)", http_status=code, retryable=True)
    if code == 429:
        raise AdapterError(ErrorType.RATE_LIMITED, "Rate limit exceeded (HTTP 429)", http_status=code, retryable=True)
    if code in (400, 422):
        raise AdapterError(ErrorType.BAD_REQUEST, f"Request rejected (HTTP {code}). {snippet}", http_status=code)
    if code >= 500:
        raise AdapterError(ErrorType.SERVER, f"Upstream server error (HTTP {code})", http_status=code, retryable=True)
    raise AdapterError(ErrorType.UNKNOWN, f"Unexpected HTTP {code}. {snippet}", http_status=code)


def _request(url: str, params: Optional[Dict[str, Any]], headers: Optional[Dict[str, str]], timeout) -> requests.Response:
    try:
        resp = _get_session().get(url, params=params, headers=headers, timeout=timeout)
    except requests.Timeout as e:
        raise AdapterError(ErrorType.TIMEOUT, f"Request timed out: {redact(e)}", retryable=True)
    except requests.ConnectionError as e:
        raise AdapterError(ErrorType.NETWORK, f"Network error: {redact(e)}", retryable=True)
    except requests.RequestException as e:
        raise AdapterError(ErrorType.NETWORK, f"Request failed: {redact(e)}")
    _raise_for_status(resp)
    return resp


def get_json(url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout=DEFAULT_TIMEOUT) -> Any:
    resp = _request(url, params, headers, timeout)
    try:
        return resp.json()
    except ValueError:
        raise AdapterError(ErrorType.BAD_RESPONSE, f"Response was not valid JSON: {redact(resp.text[:120])}")


def get_text(url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout=DEFAULT_TIMEOUT) -> str:
    return _request(url, params, headers, timeout).text
