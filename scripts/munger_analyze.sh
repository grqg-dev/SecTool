#!/usr/bin/env bash
# munger_analyze.sh — Extract focused financial data via jq, then feed it
# to an AI CLI (claude -p by default) with a Charlie Munger analysis prompt.
#
# Usage: munger_analyze.sh <data.json> <output.md> <TICKER>
#
# The data.json is the full SEC EDGAR dump for one ticker.  Rather than
# shoving the whole thing into the prompt, we use jq to carve out the
# pieces the AI actually needs:
#   1. Company metadata (tiny)
#   2. Key annual financial metrics pivoted by concept (focused)
#   3. Key quarterly metrics for recent quarters (focused)
#   4. Recent important filings list (compact)
#
# Environment variables:
#   AI_CLI        — command to invoke (default: "claude")
#   AI_CLI_ARGS   — extra args      (default: "-p --output-format text")
#   AI_MODEL      — model flag       (default: "" — use CLI default)

set -euo pipefail

DATA_FILE="${1:?Usage: $0 <data.json> <output.md> <TICKER>}"
REPORT_FILE="${2:?Usage: $0 <data.json> <output.md> <TICKER>}"
TICKER="${3:?Usage: $0 <data.json> <output.md> <TICKER>}"

AI_CLI="${AI_CLI:-claude}"
AI_CLI_ARGS="${AI_CLI_ARGS:--p --output-format text}"
AI_MODEL="${AI_MODEL:-}"

# ── Step 1: Extract company metadata ─────────────────────────────────
COMPANY=$(jq -r '{
  name: .company.name,
  cik: .cik,
  ticker: .ticker,
  entityType: .company.entityType,
  sic: .company.sic,
  sicDescription: .company.sicDescription,
  stateOfIncorporation: .company.stateOfIncorporation,
  fiscalYearEnd: .company.fiscalYearEnd,
  tickers: .company.tickers,
  exchanges: .company.exchanges
}' "$DATA_FILE")

# ── Step 2: Extract annual key financial metrics (last 10 years) ─────
ANNUAL_METRICS=$(jq '
  [.facts[]
   | select(.fp == "FY" and .canonical_tag != null)
   | {tag: .canonical_tag, year: .fy, value: .value, unit: .unit, form: .form}
  ]
  | group_by(.tag)
  | map({
      concept: .[0].tag,
      annual: (
        [.[] | {year, value, unit}]
        | unique_by(.year)
        | sort_by(.year)
        | reverse
        | .[0:10]
      )
    })
  | sort_by(.concept)
' "$DATA_FILE")

# ── Step 3: Extract recent quarterly metrics (last 8 quarters) ──────
QUARTERLY_METRICS=$(jq '
  [.facts[]
   | select((.fp == "Q1" or .fp == "Q2" or .fp == "Q3" or .fp == "Q4")
     and .canonical_tag != null)
   | {tag: .canonical_tag, fy: .fy, fp: .fp, value: .value, unit: .unit}
  ]
  | group_by(.tag)
  | map({
      concept: .[0].tag,
      quarterly: (
        [.[] | {fy, fp, value, unit}]
        | unique_by([.fy, .fp] | join("-"))
        | sort_by([.fy, .fp] | join("-"))
        | reverse
        | .[0:8]
      )
    })
  | sort_by(.concept)
' "$DATA_FILE")

# ── Step 4: Extract recent key filings ───────────────────────────────
RECENT_FILINGS=$(jq '
  [.filings[]
   | select(.isKeyForm == true)
  ]
  | sort_by(.filingDate)
  | reverse
  | .[0:15]
  | map({form, filingDate, reportDate, primaryDocument})
' "$DATA_FILE")

# ── Step 5: Filing type distribution ─────────────────────────────────
FILING_COUNTS=$(jq '
  [.filings[].form]
  | group_by(.)
  | map({form: .[0], count: length})
  | sort_by(.count)
  | reverse
  | .[0:10]
' "$DATA_FILE")

# ── Step 6: Compose the prompt ───────────────────────────────────────
PROMPT=$(cat <<PROMPT_EOF
You are Charlie Munger — the legendary investor, vice chairman of Berkshire
Hathaway, and Warren Buffett's partner for over 60 years.  You are famous for
your multidisciplinary mental models, your emphasis on quality businesses at
fair prices, your disdain for excessive leverage, your focus on durable
competitive advantages ("moats"), and your brutally honest, often contrarian
commentary.

You have been given the SEC EDGAR financial data for **${TICKER}**.  Analyze it
the way Charlie Munger would: look at the long-term trends, the quality of
earnings, the balance sheet strength, the capital allocation, and whether this
business has a durable competitive advantage.

Your analysis should be structured as a markdown report with these sections:

## Business Quality Assessment
Evaluate the nature of the business.  Is it simple and understandable?  Does it
have a moat?  What are the key economic characteristics?

## Financial Health
Analyze the balance sheet (assets, liabilities, equity), earnings quality, and
cash generation.  Look for red flags: excessive debt, declining margins,
accounting games.

## Long-Term Trends
Track revenue, net income, and EPS over the available years.  Are they growing?
Consistent?  Cyclical?  What story do the numbers tell?

## Capital Allocation
How has management deployed capital?  Look at trends in equity, debt, and
earnings retention.  Are they building value or destroying it?

## The Munger Verdict
Give your honest, characteristically blunt Charlie Munger opinion.  Would you
want to own this business for 10+ years?  What price would make it interesting?
What would make you walk away?

Use specific numbers from the data.  Format large numbers in human-readable
form (e.g., \$394.3B not 394328000000).  Be opinionated and direct — that's
what Charlie Munger would do.

---

### Company Information
\`\`\`json
${COMPANY}
\`\`\`

### Annual Financial Metrics (Key Concepts, Last 10 Years)
\`\`\`json
${ANNUAL_METRICS}
\`\`\`

### Recent Quarterly Metrics (Last 8 Quarters)
\`\`\`json
${QUARTERLY_METRICS}
\`\`\`

### Recent Key Filings
\`\`\`json
${RECENT_FILINGS}
\`\`\`

### Filing Type Distribution
\`\`\`json
${FILING_COUNTS}
\`\`\`
PROMPT_EOF
)

# ── Step 7: Run the AI ───────────────────────────────────────────────
MODEL_FLAG=""
if [ -n "$AI_MODEL" ]; then
  MODEL_FLAG="--model $AI_MODEL"
fi

# shellcheck disable=SC2086
echo "$PROMPT" | $AI_CLI $AI_CLI_ARGS $MODEL_FLAG > "$REPORT_FILE"

echo "Report written to $REPORT_FILE" >&2
