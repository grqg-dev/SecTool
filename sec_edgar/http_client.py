"""Shared HTTP client with rate limiting, retries, and SEC-compliant headers."""

import time
import requests

from sec_edgar.config import (
    MAX_RETRIES,
    BACKOFF_BASE,
    REQUEST_DELAY,
    USER_AGENT,
)

_last_request_time = 0.0


def _rate_limit():
    """Block until enough time has elapsed since the last request."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.monotonic()


def get(url: str, user_agent: str | None = None) -> requests.Response:
    """
    GET *url* with rate limiting, retries, and the required User-Agent header.

    Raises ``requests.HTTPError`` after exhausting retries on 4xx/5xx responses
    (except 403/429 which trigger backoff).
    """
    ua = user_agent or USER_AGENT
    headers = {
        "User-Agent": ua,
        "Accept-Encoding": "gzip, deflate",
    }

    for attempt in range(MAX_RETRIES + 1):
        _rate_limit()
        resp = requests.get(url, headers=headers, timeout=30)

        if resp.status_code == 200:
            return resp

        if resp.status_code in (403, 429) and attempt < MAX_RETRIES:
            wait = BACKOFF_BASE * (2 ** attempt)
            time.sleep(wait)
            continue

        resp.raise_for_status()

    # Should not reach here, but just in case:
    resp.raise_for_status()
    return resp  # pragma: no cover
