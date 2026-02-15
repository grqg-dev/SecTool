"""Stage 4 — Normalize, deduplicate, and align XBRL financial data."""

from sec_edgar.config import TAG_ALIASES, PRIORITY_CONCEPTS


def normalize_tag(tag: str) -> str:
    """Map variant XBRL tag names to a canonical name."""
    return TAG_ALIASES.get(tag, tag)


def deduplicate(rows: list[dict]) -> list[dict]:
    """
    Remove duplicate facts.

    The same data point often appears in both an original filing and its
    amendment (10-K/A).  Keep the row with the latest ``filed`` date for each
    unique (tag, end, fy, fp, unit) combination.
    """
    best: dict[tuple, dict] = {}
    for row in rows:
        key = (
            normalize_tag(row["tag"]),
            row.get("end"),
            row.get("fy"),
            row.get("fp"),
            row.get("unit"),
        )
        existing = best.get(key)
        if existing is None or (row.get("filed", "") > existing.get("filed", "")):
            best[key] = row
    return list(best.values())


def filter_priority(rows: list[dict]) -> list[dict]:
    """Keep only rows whose tag (after alias resolution) is in PRIORITY_CONCEPTS."""
    canonical = set(PRIORITY_CONCEPTS)
    return [r for r in rows if normalize_tag(r["tag"]) in canonical]


def normalize(
    facts_rows: list[dict],
    priority_only: bool = False,
) -> list[dict]:
    """
    Full normalisation pipeline:

    1. Add a ``canonical_tag`` field via alias resolution.
    2. Deduplicate.
    3. Optionally filter to priority concepts only.
    4. Sort by (canonical_tag, end date, fiscal year).
    """
    # 1. Canonical tag
    for row in facts_rows:
        row["canonical_tag"] = normalize_tag(row["tag"])

    # 2. Deduplicate
    rows = deduplicate(facts_rows)

    # 3. Filter
    if priority_only:
        rows = filter_priority(rows)

    # 4. Sort
    rows.sort(key=lambda r: (r["canonical_tag"], r.get("end") or "", r.get("fy") or 0))

    return rows
