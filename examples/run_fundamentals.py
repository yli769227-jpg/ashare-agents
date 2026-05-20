"""
Demo: run FundamentalsAnalyst on a given ticker.

Usage:
    python examples/run_fundamentals.py 000001          # default 5-year window
    python examples/run_fundamentals.py 600036 --years 3

If OPENAI_API_KEY is set in env (or .env), uses real ChatOpenAI.
Otherwise uses FakeLLM and still does a real ashare-mcp data fetch.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:
    pass

from ashare_agents.orchestrator import run

logging.basicConfig(level=logging.INFO)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run FundamentalsAnalyst on a single ticker.")
    ap.add_argument("ticker", help="A-share code, e.g. 000001 / SH600036 / 300750.SZ")
    ap.add_argument("--years", type=int, default=5, help="History window (default 5)")
    args = ap.parse_args()

    state = run(args.ticker)
    err = state.get("error")
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    view = state["fundamentals"]
    print(json.dumps(view.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
