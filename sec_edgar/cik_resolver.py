"""Stage 1 — Resolve ticker symbols to SEC CIK identifiers."""

import json
import os
import time
from difflib import get_close_matches

from sec_edgar.config import CACHE_DIR, TICKER_MAP_URL, TICKER_CACHE_MAX_AGE_HOURS
from sec_edgar import http_client


def _cache_path() -> str:
    return os.path.join(CACHE_DIR, "company_tickers.json")


def _cache_is_fresh() -> bool:
    path = _cache_path()
    if not os.path.exists(path):
        return False
    age_hours = (time.time() - os.path.getmtime(path)) / 3600
    return age_hours < TICKER_CACHE_MAX_AGE_HOURS


def _load_ticker_map(user_agent: str | None = None) -> dict:
    """
    Return ``{TICKER: {"cik_str": int, "ticker": str, "title": str}, ...}``.

    Uses a local file cache that refreshes daily.
    """
    if _cache_is_fresh():
        with open(_cache_path()) as f:
            raw = json.load(f)
    else:
        resp = http_client.get(TICKER_MAP_URL, user_agent=user_agent)
        raw = resp.json()
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(), "w") as f:
            json.dump(raw, f)

    # The SEC file is keyed by index ("0", "1", …). Build a ticker-keyed dict.
    ticker_map: dict[str, dict] = {}
    for entry in raw.values():
        ticker_map[entry["ticker"].upper()] = entry
    return ticker_map


def resolve(
    tickers: list[str],
    user_agent: str | None = None,
) -> dict[str, str]:
    """
    Resolve *tickers* to zero-padded 10-digit CIK strings.

    Returns ``{TICKER: "0000320193", ...}``.
    Raises ``KeyError`` for any ticker that cannot be found (with suggestions).
    """
    ticker_map = _load_ticker_map(user_agent=user_agent)
    results: dict[str, str] = {}
    all_tickers = list(ticker_map.keys())

    for t in tickers:
        key = t.strip().upper()
        if key in ticker_map:
            cik = ticker_map[key]["cik_str"]
            results[key] = str(cik).zfill(10)
        else:
            close = get_close_matches(key, all_tickers, n=5, cutoff=0.6)
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            raise KeyError(f"Ticker '{key}' not found in SEC data.{hint}")

    return results
