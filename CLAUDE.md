# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SEC EDGAR CLI tool (`sec-edgar`) that retrieves filing metadata and XBRL financial data by stock ticker symbol. Python 3.10+, single dependency (`requests`).

## Commands

```bash
# Install (editable mode, uses venv)
source venv/bin/activate
pip install -e .

# Run
sec-edgar AAPL                              # JSON output to ./output/
sec-edgar AAPL MSFT --format csv            # CSV output
sec-edgar AAPL --format sqlite              # SQLite output
sec-edgar AAPL --filings-only               # Skip XBRL facts
sec-edgar AAPL --facts-only --priority-only # Only key financial metrics
```

No test suite exists yet. No linter configuration.

## Architecture

Four-stage pipeline per ticker, orchestrated by `sec_edgar/main.py`:

1. **Resolve** (`cik_resolver.py`) — Maps ticker symbols to 10-digit CIK strings via SEC's `company_tickers.json`. Caches the full ticker map locally (`~/.sec_edgar_cache/`) for 24 hours.
2. **Submissions** (`submissions.py`) — Fetches filing metadata from SEC submissions API. Handles pagination via overflow files.
3. **Company Facts** (`company_facts.py`) — Retrieves XBRL financial facts. `extract_facts_flat()` flattens the nested taxonomy→concept→unit→entries structure into flat dicts.
4. **Normalize & Output** (`normalizer.py`, `storage.py`) — Resolves XBRL tag aliases to canonical names (e.g., multiple revenue tags → `Revenues`), deduplicates by keeping latest filing date, optionally filters to priority concepts. Writes to JSON/CSV/SQLite.

**Shared HTTP client** (`http_client.py`) — All SEC API calls go through `http_client.get()` which enforces rate limiting (max 8 req/s) and exponential backoff on 403/429.

**Configuration** (`config.py`) — SEC API URLs, rate limits, retry settings, `PRIORITY_CONCEPTS` list, and `TAG_ALIASES` mapping. User-Agent is read from `SEC_EDGAR_USER_AGENT` env var.

## Key Design Notes

- SEC requires a descriptive `User-Agent` header with contact info; set via `--user-agent` flag or `SEC_EDGAR_USER_AGENT` env var
- CIK strings are always zero-padded to 10 digits
- The SEC submissions API returns filings in parallel-array format (keys map to arrays of values) — `_parse_filings()` converts this to list-of-dicts
- Tag normalization happens via `TAG_ALIASES` dict in `config.py`; add new aliases there when SEC companies use non-standard XBRL tags
