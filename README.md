# sec-edgar-cli

A command-line tool for retrieving SEC EDGAR filing metadata and XBRL financial data by stock ticker symbol.

## Features

- Resolve stock ticker symbols to SEC CIK identifiers
- Fetch filing metadata (10-K, 10-Q, 8-K, and more)
- Retrieve XBRL-tagged financial facts (revenue, net income, EPS, assets, etc.)
- Normalize variant XBRL tag names and deduplicate records
- Output to JSON, CSV, or SQLite
- Built-in rate limiting and retry logic for SEC API compliance

## Requirements

- Python 3.10+

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install -r requirements.txt
```

## Usage

After installation the `sec-edgar` command is available:

```bash
sec-edgar TICKER [TICKER ...] [options]
```

### Examples

```bash
# Fetch all data for Apple as JSON (default)
sec-edgar AAPL

# Multiple tickers, CSV output
sec-edgar AAPL MSFT GOOG --format csv --output-dir financial_data

# Only 10-K filing metadata
sec-edgar AAPL --forms 10-K --filings-only

# Priority financial metrics to SQLite
sec-edgar AAPL MSFT --format sqlite --priority-only
```

### Options

| Flag | Description |
|---|---|
| `--format {csv,json,sqlite}` | Output format (default: `json`) |
| `--output-dir DIR` | Directory for output files (default: `./output`) |
| `--db PATH` | SQLite database path (default: `<output-dir>/sec_edgar.db`) |
| `--filings-only` | Fetch filing metadata only, skip XBRL facts |
| `--facts-only` | Fetch XBRL facts only, skip filing metadata |
| `--priority-only` | Keep only priority financial concepts |
| `--forms FORM [FORM ...]` | Filter to specific form types (e.g., `10-K 10-Q`) |
| `--user-agent STRING` | SEC-compliant User-Agent (defaults to `$SEC_EDGAR_USER_AGENT`) |

## Output Formats

**JSON** — One `{TICKER}.json` file per ticker containing company metadata, filings, and normalized facts.

**CSV** — Two files per ticker: `{TICKER}_filings.csv` and `{TICKER}_facts.csv`.

**SQLite** — Single database with `companies`, `filings`, and `facts` tables.

## How It Works

The tool runs a four-stage pipeline for each ticker:

1. **Resolve** — Map ticker symbol to SEC CIK number using the SEC company tickers endpoint. Results are cached locally for 24 hours.
2. **Filings** — Fetch filing metadata from the SEC submissions API, with pagination support.
3. **Facts** — Retrieve XBRL financial facts from the SEC company facts API.
4. **Normalize & Output** — Deduplicate records, normalize tag names, and write results in the selected format.

## SEC API Compliance

The tool respects SEC EDGAR rate limits (max 8 requests/second) and uses exponential backoff for transient errors. Set a proper User-Agent string via `--user-agent` or the `SEC_EDGAR_USER_AGENT` environment variable as required by SEC policy.

## License

See [LICENSE](LICENSE) if available.
