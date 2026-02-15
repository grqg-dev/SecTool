"""Stage 3 — Fetch XBRL company facts from SEC EDGAR."""

from sec_edgar.config import COMPANY_FACTS_URL, COMPANY_CONCEPT_URL
from sec_edgar import http_client


def fetch(cik: str, user_agent: str | None = None) -> dict:
    """
    Fetch all XBRL-tagged financial facts for *cik*.

    Returns the raw JSON dict keyed by taxonomy → concept → units → values.
    Returns an empty dict if the company has no XBRL data.
    """
    url = COMPANY_FACTS_URL.format(cik=cik)
    try:
        data = http_client.get(url, user_agent=user_agent).json()
    except Exception:
        # Company may not have XBRL data (e.g., foreign private issuers)
        return {}
    return data


def fetch_concept(
    cik: str,
    taxonomy: str,
    tag: str,
    user_agent: str | None = None,
) -> dict:
    """
    Fetch a single XBRL concept time series.

    Useful for targeted queries (e.g., ``us-gaap/Revenues``).
    """
    url = COMPANY_CONCEPT_URL.format(cik=cik, taxonomy=taxonomy, tag=tag)
    try:
        data = http_client.get(url, user_agent=user_agent).json()
    except Exception:
        return {}
    return data


def extract_facts_flat(facts_data: dict) -> list[dict]:
    """
    Flatten the nested Company Facts response into a list of records.

    Each record looks like::

        {
            "taxonomy": "us-gaap",
            "tag": "Revenues",
            "unit": "USD",
            "value": 394328000000,
            "end": "2023-09-30",
            "start": "2022-10-01",
            "fy": 2023,
            "fp": "FY",
            "form": "10-K",
            "filed": "2023-11-03",
            "accn": "0000320193-23-000106",
        }
    """
    rows: list[dict] = []
    facts = facts_data.get("facts", {})
    for taxonomy, concepts in facts.items():
        for tag, tag_data in concepts.items():
            label = tag_data.get("label", tag)
            description = tag_data.get("description", "")
            units = tag_data.get("units", {})
            for unit, entries in units.items():
                for entry in entries:
                    row = {
                        "taxonomy": taxonomy,
                        "tag": tag,
                        "label": label,
                        "description": description,
                        "unit": unit,
                        "value": entry.get("val"),
                        "end": entry.get("end"),
                        "start": entry.get("start"),
                        "fy": entry.get("fy"),
                        "fp": entry.get("fp"),
                        "form": entry.get("form"),
                        "filed": entry.get("filed"),
                        "accn": entry.get("accn"),
                    }
                    rows.append(row)
    return rows
