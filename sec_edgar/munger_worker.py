"""Background worker for Charlie Munger analysis jobs.

Fetches SEC data via the existing pipeline, prepares a focused financial
summary, then shells out to the analysis script which feeds the data to
an AI CLI (claude -p by default) for a "What Would Charlie Munger Do" report.
"""

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from sec_edgar import cik_resolver, submissions, company_facts
from sec_edgar.company_facts import extract_facts_flat
from sec_edgar.normalizer import normalize
from sec_edgar.config import USER_AGENT

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
ANALYZE_SCRIPT = SCRIPTS_DIR / "munger_analyze.sh"


def _fetch_ticker_data(ticker: str, user_agent: str | None = None) -> dict:
    """Run stages 1-3 of the SEC pipeline and return structured data."""
    ua = user_agent or USER_AGENT

    cik_map = cik_resolver.resolve([ticker], user_agent=ua)
    cik = cik_map[ticker]

    sub = submissions.fetch(cik, user_agent=ua)
    company = sub["company"]
    filings = sub["filings"]

    raw_facts = company_facts.fetch(cik, user_agent=ua)
    if raw_facts:
        flat = extract_facts_flat(raw_facts)
        facts = normalize(flat, priority_only=False)
    else:
        facts = []

    return {
        "ticker": ticker,
        "cik": cik,
        "company": company,
        "filings": filings,
        "facts": facts,
    }


def _prepare_summary(data: dict, work_dir: str) -> str:
    """Write full JSON and return the path.

    The shell script uses jq to extract focused slices from this file,
    so the AI never has to ingest the entire blob at once.
    """
    full_path = os.path.join(work_dir, "full_data.json")
    with open(full_path, "w") as f:
        json.dump(data, f, default=str)
    return full_path


def run_analysis(ticker: str, user_agent: str | None = None,
                 on_progress=None) -> str:
    """End-to-end: fetch data → prepare → run AI analysis → return markdown.

    *on_progress* is an optional callback ``(stage: str) -> None`` called
    as the job moves through stages.
    """
    def _progress(stage: str):
        if on_progress:
            on_progress(stage)

    _progress("resolving_ticker")

    # Fetch all SEC data
    _progress("fetching_data")
    data = _fetch_ticker_data(ticker, user_agent=user_agent)

    filing_count = len(data.get("filings", []))
    fact_count = len(data.get("facts", []))
    _progress(f"data_ready:filings={filing_count},facts={fact_count}")

    # Prepare data files in a temp directory
    with tempfile.TemporaryDirectory(prefix="munger_") as work_dir:
        data_path = _prepare_summary(data, work_dir)
        report_path = os.path.join(work_dir, "report.md")

        # Run the analysis shell script
        _progress("analyzing")
        result = subprocess.run(
            ["bash", str(ANALYZE_SCRIPT), data_path, report_path, ticker],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute max
            env={**os.environ, "CLAUDECODE": ""},  # bypass nesting check
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Analysis script failed (exit {result.returncode}): {stderr}"
            )

        if not os.path.exists(report_path):
            # Script may have written to stdout instead
            if result.stdout.strip():
                return result.stdout.strip()
            raise RuntimeError("Analysis script produced no output")

        with open(report_path) as f:
            return f.read()
