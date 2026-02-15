"""CLI entrypoint for SEC EDGAR data retrieval."""

import argparse
import os
import sys

from sec_edgar import cik_resolver, submissions, company_facts, http_client
from sec_edgar.company_facts import extract_facts_flat
from sec_edgar.normalizer import normalize
from sec_edgar.storage import write_csv, write_json, write_sqlite
from sec_edgar.config import USER_AGENT


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sec-edgar",
        description="Retrieve SEC EDGAR filing metadata and XBRL financial data for one or more tickers.",
    )
    p.add_argument(
        "tickers",
        nargs="+",
        metavar="TICKER",
        help="One or more stock ticker symbols (e.g. AAPL MSFT GOOG).",
    )
    p.add_argument(
        "--user-agent",
        default=None,
        help=(
            "SEC-compliant User-Agent string (company/app name + email). "
            "Defaults to $SEC_EDGAR_USER_AGENT or a placeholder."
        ),
    )

    # Output format
    fmt = p.add_argument_group("output format")
    fmt.add_argument(
        "--format",
        choices=["csv", "json", "sqlite"],
        default="json",
        help="Output format (default: json).",
    )
    fmt.add_argument(
        "--output-dir",
        default="output",
        help="Directory for output files (default: ./output).",
    )
    fmt.add_argument(
        "--db",
        default=None,
        help="SQLite database path (only used with --format sqlite). "
        "Defaults to <output-dir>/sec_edgar.db.",
    )

    # Data selection
    data = p.add_argument_group("data selection")
    data.add_argument(
        "--filings-only",
        action="store_true",
        help="Fetch filing metadata only (skip XBRL facts).",
    )
    data.add_argument(
        "--facts-only",
        action="store_true",
        help="Fetch XBRL facts only (skip filing metadata).",
    )
    data.add_argument(
        "--priority-only",
        action="store_true",
        help="Keep only priority financial concepts (Revenue, Net Income, EPS, etc.).",
    )
    data.add_argument(
        "--forms",
        nargs="+",
        metavar="FORM",
        default=None,
        help="Filter filings to these form types (e.g. 10-K 10-Q).",
    )
    return p


def _run_ticker(
    ticker: str,
    cik: str,
    args: argparse.Namespace,
) -> dict:
    """Fetch, normalise, and store data for a single ticker. Returns summary."""
    ua = args.user_agent
    result: dict = {"ticker": ticker, "cik": cik}

    # ── Submissions ──────────────────────────────────────────────────────
    if not args.facts_only:
        print(f"  [{ticker}] Fetching submissions …")
        sub = submissions.fetch(cik, user_agent=ua)
        result["company"] = sub["company"]
        filings = sub["filings"]
        if args.forms:
            form_set = {f.upper() for f in args.forms}
            filings = [f for f in filings if f.get("form", "").upper() in form_set]
        result["filings"] = filings
        print(f"  [{ticker}] {len(filings)} filings retrieved.")
    else:
        result["company"] = {}
        result["filings"] = []

    # ── Company Facts ────────────────────────────────────────────────────
    if not args.filings_only:
        print(f"  [{ticker}] Fetching company facts …")
        raw_facts = company_facts.fetch(cik, user_agent=ua)
        if raw_facts:
            flat = extract_facts_flat(raw_facts)
            rows = normalize(flat, priority_only=args.priority_only)
            result["facts"] = rows
            print(f"  [{ticker}] {len(rows)} fact records after normalisation.")
        else:
            result["facts"] = []
            print(f"  [{ticker}] No XBRL data available.")
    else:
        result["facts"] = []

    # ── Write output ─────────────────────────────────────────────────────
    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)
    fmt = args.format

    if fmt == "json":
        path = os.path.join(out_dir, f"{ticker}.json")
        write_json(result, path)
        print(f"  [{ticker}] Written → {path}")

    elif fmt == "csv":
        if result["filings"]:
            fp = os.path.join(out_dir, f"{ticker}_filings.csv")
            write_csv(result["filings"], fp)
            print(f"  [{ticker}] Filings → {fp}")
        if result["facts"]:
            fp = os.path.join(out_dir, f"{ticker}_facts.csv")
            write_csv(result["facts"], fp)
            print(f"  [{ticker}] Facts   → {fp}")

    elif fmt == "sqlite":
        db = args.db or os.path.join(out_dir, "sec_edgar.db")
        write_sqlite(ticker, result["company"], result["filings"], result["facts"], db)
        print(f"  [{ticker}] Written → {db}")

    return result


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    ua = args.user_agent or USER_AGENT
    args.user_agent = ua

    # ── Stage 1: Resolve tickers ─────────────────────────────────────────
    print("Resolving tickers …")
    try:
        cik_map = cik_resolver.resolve(args.tickers, user_agent=ua)
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for ticker, cik in cik_map.items():
        print(f"  {ticker} → CIK {cik}")

    # ── Stages 2-4: Fetch & process each ticker ─────────────────────────
    for ticker, cik in cik_map.items():
        print(f"\nProcessing {ticker} …")
        try:
            _run_ticker(ticker, cik, args)
        except Exception as exc:
            print(f"  [{ticker}] Error: {exc}", file=sys.stderr)
            continue

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
