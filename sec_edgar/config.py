"""Configuration for SEC EDGAR data retrieval."""

import os

# SEC EDGAR API endpoints
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
COMPANY_CONCEPT_URL = (
    "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"
)

# User-Agent header — SEC requires a descriptive UA with contact info.
# Override via environment variable or pass directly to the CLI.
USER_AGENT = os.environ.get(
    "SEC_EDGAR_USER_AGENT",
    "SecEdgarCLI/1.0 (contact@example.com)",
)

# Rate limiting
MAX_REQUESTS_PER_SECOND = 8  # SEC cap is 10; stay conservative
REQUEST_DELAY = 1.0 / MAX_REQUESTS_PER_SECOND

# Retry / backoff
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds; doubles each retry

# Local cache directory
CACHE_DIR = os.environ.get(
    "SEC_EDGAR_CACHE_DIR",
    os.path.join(os.path.expanduser("~"), ".sec_edgar_cache"),
)
TICKER_CACHE_MAX_AGE_HOURS = 24

# Key XBRL concept tags used for financial analysis (us-gaap taxonomy)
PRIORITY_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "OperatingIncomeLoss",
    "CashAndCashEquivalentsAtCarryingValue",
    "CommonStockSharesOutstanding",
]

# Tag aliases — normalise variant tags to a canonical name
TAG_ALIASES = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax": "Revenues",
    "SalesRevenueNet": "Revenues",
    "SalesRevenueGoodsNet": "Revenues",
    "SalesRevenueServicesNet": "Revenues",
    "NetIncomeLossAvailableToCommonStockholdersBasic": "NetIncomeLoss",
}

# Filing form types worth flagging
KEY_FORM_TYPES = {"10-K", "10-Q", "8-K", "DEF 14A", "S-1"}
