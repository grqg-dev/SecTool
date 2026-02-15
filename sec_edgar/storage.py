"""Output writers — CSV, JSON, and SQLite."""

import csv
import json
import os
import sqlite3


# ── CSV ──────────────────────────────────────────────────────────────────────

def write_csv(rows: list[dict], path: str) -> str:
    """Write *rows* (list of flat dicts) to a CSV file. Returns the path."""
    if not rows:
        return path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


# ── JSON ─────────────────────────────────────────────────────────────────────

def write_json(data, path: str) -> str:
    """Write any JSON-serialisable *data* to a file. Returns the path."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


# ── SQLite ───────────────────────────────────────────────────────────────────

_FACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    ticker        TEXT,
    taxonomy      TEXT,
    tag           TEXT,
    canonical_tag TEXT,
    label         TEXT,
    unit          TEXT,
    value         REAL,
    end_date      TEXT,
    start_date    TEXT,
    fy            INTEGER,
    fp            TEXT,
    form          TEXT,
    filed         TEXT,
    accn          TEXT
);
"""

_FILINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS filings (
    ticker           TEXT,
    form             TEXT,
    filing_date      TEXT,
    accession_number TEXT,
    primary_document TEXT,
    is_key_form      INTEGER
);
"""

_COMPANY_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    ticker               TEXT PRIMARY KEY,
    cik                  TEXT,
    name                 TEXT,
    entity_type          TEXT,
    sic                  TEXT,
    sic_description      TEXT,
    state_of_inc         TEXT,
    fiscal_year_end      TEXT
);
"""


def write_sqlite(
    ticker: str,
    company: dict,
    filings: list[dict],
    facts: list[dict],
    db_path: str,
) -> str:
    """
    Upsert company, filings, and facts for *ticker* into a SQLite database.
    Returns the database path.
    """
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(_COMPANY_SCHEMA + _FILINGS_SCHEMA + _FACTS_SCHEMA)

    # Company
    cur.execute("DELETE FROM companies WHERE ticker = ?", (ticker,))
    cur.execute(
        "INSERT INTO companies VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ticker,
            company.get("cik"),
            company.get("name"),
            company.get("entityType"),
            company.get("sic"),
            company.get("sicDescription"),
            company.get("stateOfIncorporation"),
            company.get("fiscalYearEnd"),
        ),
    )

    # Filings
    cur.execute("DELETE FROM filings WHERE ticker = ?", (ticker,))
    for f in filings:
        cur.execute(
            "INSERT INTO filings VALUES (?, ?, ?, ?, ?, ?)",
            (
                ticker,
                f.get("form"),
                f.get("filingDate"),
                f.get("accessionNumber"),
                f.get("primaryDocument"),
                int(f.get("isKeyForm", False)),
            ),
        )

    # Facts
    cur.execute("DELETE FROM facts WHERE ticker = ?", (ticker,))
    for r in facts:
        cur.execute(
            "INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ticker,
                r.get("taxonomy"),
                r.get("tag"),
                r.get("canonical_tag"),
                r.get("label"),
                r.get("unit"),
                r.get("value"),
                r.get("end"),
                r.get("start"),
                r.get("fy"),
                r.get("fp"),
                r.get("form"),
                r.get("filed"),
                r.get("accn"),
            ),
        )

    con.commit()
    con.close()
    return db_path
