"""Stage 2 — Fetch and parse SEC filing submissions for a company."""

from sec_edgar.config import SUBMISSIONS_URL, KEY_FORM_TYPES
from sec_edgar import http_client


def _parse_filings(recent: dict) -> list[dict]:
    """Turn the parallel-array format into a list of filing dicts."""
    keys = list(recent.keys())
    count = len(recent[keys[0]]) if keys else 0
    filings = []
    for i in range(count):
        filing = {k: recent[k][i] for k in keys}
        filing["isKeyForm"] = filing.get("form", "") in KEY_FORM_TYPES
        filings.append(filing)
    return filings


def fetch(cik: str, user_agent: str | None = None) -> dict:
    """
    Fetch submissions for *cik* (10-digit padded string).

    Returns::

        {
            "company": { name, cik, sic, sicDescription, stateOfIncorporation,
                         fiscalYearEnd, ... },
            "filings": [ { form, filingDate, accessionNumber,
                           primaryDocument, isKeyForm, ... }, ... ],
        }
    """
    url = SUBMISSIONS_URL.format(cik=cik)
    data = http_client.get(url, user_agent=user_agent).json()

    company = {
        "cik": data.get("cik"),
        "name": data.get("name"),
        "entityType": data.get("entityType"),
        "sic": data.get("sic"),
        "sicDescription": data.get("sicDescription"),
        "stateOfIncorporation": data.get("stateOfIncorporation"),
        "fiscalYearEnd": data.get("fiscalYearEnd"),
        "tickers": data.get("tickers", []),
        "exchanges": data.get("exchanges", []),
    }

    # Recent filings are in data["filings"]["recent"]
    recent = data.get("filings", {}).get("recent", {})
    filings = _parse_filings(recent)

    # Handle pagination — overflow files listed in data["filings"]["files"]
    overflow_files = data.get("filings", {}).get("files", [])
    for ref in overflow_files:
        overflow_url = f"https://data.sec.gov/submissions/{ref['name']}"
        overflow_data = http_client.get(overflow_url, user_agent=user_agent).json()
        filings.extend(_parse_filings(overflow_data))

    return {"company": company, "filings": filings}
