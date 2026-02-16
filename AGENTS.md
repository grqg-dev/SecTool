# AGENTS.md

Reference for AI agents consuming SEC EDGAR CLI output data.

## Quick Start

```bash
# Fetch data for a ticker (outputs to ./output/)
sec-edgar AAPL

# Multiple tickers
sec-edgar AAPL MSFT GOOG

# Only key financial metrics
sec-edgar AAPL --priority-only

# CSV output
sec-edgar AAPL --format csv

# Browse data in browser
python3 serve.py  # http://localhost:8000
```

Set `SEC_EDGAR_USER_AGENT` env var to a string like `"MyApp/1.0 (me@example.com)"` — SEC requires this.

## CLI Flags

| Flag | Effect |
|---|---|
| `--format {json,csv,sqlite}` | Output format (default: `json`) |
| `--output-dir DIR` | Output directory (default: `./output`) |
| `--db PATH` | SQLite path (default: `<output-dir>/sec_edgar.db`) |
| `--filings-only` | Skip XBRL facts, only get filing metadata |
| `--facts-only` | Skip filings, only get financial facts |
| `--priority-only` | Keep only priority financial concepts (see list below) |
| `--forms FORM [...]` | Filter to specific form types (e.g. `10-K 10-Q`) |
| `--user-agent STRING` | Override User-Agent (default: `$SEC_EDGAR_USER_AGENT`) |

## Output Files

- **JSON**: `output/{TICKER}.json` — one file per ticker
- **CSV**: `output/{TICKER}_filings.csv` + `output/{TICKER}_facts.csv` — two files per ticker
- **SQLite**: `output/sec_edgar.db` — single database, tables: `companies`, `filings`, `facts`

---

## JSON Data Dictionary

Each `{TICKER}.json` has this top-level structure:

```json
{
  "ticker": "AAPL",
  "cik": "0000320193",
  "company": { ... },
  "filings": [ ... ],
  "facts": [ ... ]
}
```

### `company` Object

| Field | Type | Example | Description |
|---|---|---|---|
| `cik` | string | `"0000320193"` | 10-digit zero-padded SEC CIK |
| `name` | string | `"Apple Inc."` | Legal entity name |
| `entityType` | string | `"operating"` | Entity classification |
| `sic` | string | `"3571"` | 4-digit Standard Industrial Classification code |
| `sicDescription` | string | `"Electronic Computers"` | SIC code description |
| `stateOfIncorporation` | string | `"CA"` | 2-letter state code |
| `fiscalYearEnd` | string | `"0926"` | MMDD format (e.g. `"0926"` = September 26) |
| `tickers` | string[] | `["AAPL"]` | Associated ticker symbols |
| `exchanges` | string[] | `["Nasdaq"]` | Stock exchanges |

### `filings` Array

Each element is a filing record. Expect ~1,000–3,000 per ticker.

| Field | Type | Example | Description |
|---|---|---|---|
| `accessionNumber` | string | `"0000320193-26-000006"` | Unique SEC filing ID |
| `filingDate` | string | `"2026-01-30"` | Date filed (YYYY-MM-DD) |
| `reportDate` | string | `"2025-12-27"` | Report period date (YYYY-MM-DD, may be empty) |
| `acceptanceDateTime` | string | `"2026-01-30T11:01:32.000Z"` | ISO 8601 acceptance timestamp |
| `form` | string | `"10-Q"` | SEC form type |
| `act` | string | `"34"` | Securities Act reference (often empty) |
| `fileNumber` | string | `"001-36743"` | SEC file number (often empty) |
| `filmNumber` | string | `"26580330"` | Film number (often empty) |
| `items` | string | `""` | Item codes (8-K filings only) |
| `core_type` | string | `"XBRL"` | Filing type code |
| `size` | integer | `5191740` | File size in bytes |
| `isXBRL` | integer | `1` | 0 or 1 |
| `isInlineXBRL` | integer | `1` | 0 or 1 |
| `primaryDocument` | string | `"aapl-20251227.htm"` | Primary document filename |
| `primaryDocDescription` | string | `"10-Q"` | Human-readable description |
| `isKeyForm` | boolean | `true` | True if form is 10-K, 10-Q, 8-K, DEF 14A, or S-1 |

**Common form types**: `10-K` (annual), `10-Q` (quarterly), `8-K` (current events), `4` (insider trades), `DEF 14A` (proxy), `S-1` (registration), `SC 13G` (ownership).

**Building SEC EDGAR URLs from a filing**:
```
https://www.sec.gov/Archives/edgar/data/{cik_no_padding}/{accn_no_dashes}/{primaryDocument}
```
Where `accn_no_dashes` = accessionNumber with dashes removed, `cik_no_padding` = integer CIK.

### `facts` Array

Each element is a normalized XBRL financial data point. Expect ~500–5,000 per ticker.

| Field | Type | Example | Description |
|---|---|---|---|
| `taxonomy` | string | `"us-gaap"` | XBRL taxonomy (usually `us-gaap`, sometimes `dei`, `ifrs-full`) |
| `tag` | string | `"RevenueFromContractWithCustomerExcludingAssessedTax"` | Original XBRL tag name |
| `canonical_tag` | string | `"Revenues"` | Normalized tag name (via alias resolution) |
| `label` | string | `"Revenue from Contract with Customer, Excluding Assessed Tax"` | Human-readable label |
| `description` | string | *(long text)* | Full XBRL semantic description |
| `unit` | string | `"USD"` | Unit of measurement |
| `value` | number\|null | `394328000000` | The data value (raw, not scaled) |
| `end` | string | `"2023-09-30"` | Period end date (YYYY-MM-DD) |
| `start` | string\|null | `"2022-10-01"` | Period start date (null for point-in-time like Assets) |
| `fy` | integer | `2023` | Fiscal year |
| `fp` | string | `"FY"` | Fiscal period: `FY`, `Q1`, `Q2`, `Q3`, `Q4` |
| `form` | string | `"10-K"` | Source form type |
| `filed` | string | `"2023-11-03"` | Date the filing was made (YYYY-MM-DD) |
| `accn` | string | `"0000320193-23-000106"` | Source accession number |

**Units**: `"USD"` (dollar amounts), `"USD/shares"` (per-share dollar amounts like EPS), `"shares"` (share counts), `"pure"` (ratios/percentages).

**Values are raw** — not scaled. `394328000000` = $394.3 billion. Your agent must format these.

**`start` is null** for point-in-time balance sheet items (Assets, Liabilities, Equity). It has a value for income/flow items (Revenue, Net Income) that cover a date range.

---

## Priority Financial Concepts

When `--priority-only` is used, only these `canonical_tag` values are kept:

| canonical_tag | What It Is | Typical Unit |
|---|---|---|
| `Revenues` | Total revenue / sales | USD |
| `NetIncomeLoss` | Net income (or loss) | USD |
| `EarningsPerShareBasic` | Basic EPS | USD/shares |
| `EarningsPerShareDiluted` | Diluted EPS | USD/shares |
| `Assets` | Total assets | USD |
| `Liabilities` | Total liabilities | USD |
| `StockholdersEquity` | Total stockholders' equity | USD |
| `OperatingIncomeLoss` | Operating income (or loss) | USD |
| `CashAndCashEquivalentsAtCarryingValue` | Cash and equivalents | USD |
| `CommonStockSharesOutstanding` | Shares outstanding | shares |

## Tag Aliases

Multiple XBRL tags map to the same concept. The `canonical_tag` field resolves these:

| Original Tag | Canonical Tag |
|---|---|
| `RevenueFromContractWithCustomerExcludingAssessedTax` | `Revenues` |
| `RevenueFromContractWithCustomerIncludingAssessedTax` | `Revenues` |
| `SalesRevenueNet` | `Revenues` |
| `SalesRevenueGoodsNet` | `Revenues` |
| `SalesRevenueServicesNet` | `Revenues` |
| `NetIncomeLossAvailableToCommonStockholdersBasic` | `NetIncomeLoss` |

**Always use `canonical_tag` for grouping/filtering, not `tag`.**

---

## SQLite Schema

Three tables, all keyed by `ticker`:

```sql
-- Company metadata (one row per ticker)
companies (
    ticker TEXT PRIMARY KEY,
    cik TEXT, name TEXT, entity_type TEXT,
    sic TEXT, sic_description TEXT,
    state_of_inc TEXT, fiscal_year_end TEXT
)

-- Filing records
filings (
    ticker TEXT, form TEXT, filing_date TEXT,
    accession_number TEXT, primary_document TEXT,
    is_key_form INTEGER  -- 0 or 1
)

-- XBRL fact records
facts (
    ticker TEXT, taxonomy TEXT, tag TEXT, canonical_tag TEXT,
    label TEXT, unit TEXT, value REAL,
    end_date TEXT, start_date TEXT,
    fy INTEGER, fp TEXT, form TEXT,
    filed TEXT, accn TEXT
)
```

**Note**: SQLite column names differ slightly from JSON keys (e.g. `end_date` vs `end`, `filing_date` vs `filingDate`).

---

## Deduplication Logic

The same financial data point often appears in both an original filing and its amendment (e.g. 10-K and 10-K/A). The normalizer deduplicates by:

1. Grouping by `(canonical_tag, end, fy, fp, unit)`
2. Keeping only the row with the latest `filed` date

This means output data is already deduplicated. No further dedup needed by consumers.

## Rate Limiting

The CLI respects SEC EDGAR rate limits (8 req/s, under the 10 req/s cap). Exponential backoff on 403/429 responses. Ticker-to-CIK mapping is cached locally at `~/.sec_edgar_cache/company_tickers.json` for 24 hours.

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `SEC_EDGAR_USER_AGENT` | HTTP User-Agent header (required by SEC) | `SecEdgarCLI/1.0 (contact@example.com)` |
| `SEC_EDGAR_CACHE_DIR` | Local cache directory | `~/.sec_edgar_cache` |
