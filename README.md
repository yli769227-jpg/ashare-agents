# ashare-agents

[![tests](https://github.com/yli769227-jpg/ashare-agents/actions/workflows/test.yml/badge.svg)](https://github.com/yli769227-jpg/ashare-agents/actions/workflows/test.yml)

**A-share agent orchestration layer.** TradingAgents-style multi-role debate
graph that consumes the [`ashare-mcp`](https://github.com/yli769227-jpg/ashare-mcp) toolset.

> **This repo does NOT reimplement what `ashare-mcp` already does.** Data
> fetch, cross-check, peer compare, history time-series, document parsing —
> all live in `ashare-mcp`. This repo is **purely orchestration**: roles,
> debate, summarization, decision routing.

---

## Layout

```
src/ashare_agents/
├── analysts.py        # FundamentalsAnalyst (implemented)
│                      # + Sentiment / News / Technical / Risk (TODO stubs)
├── researchers.py     # BullishResearcher / BearishResearcher (TODO stubs)
├── trader.py          # TraderAgent (TODO stub)
├── portfolio_manager.py # PortfolioManager (TODO stub)
└── orchestrator.py    # LangGraph wiring — currently single-node graph
                       # that just runs FundamentalsAnalyst
```

## What works today

1. `FundamentalsAnalyst.analyze(ticker)`:
   1. Calls `ashare_mcp.history.track_company_history_impl(ticker, years=5)`
      to fetch 5-year three-statement series + YoY / CAGR / anomalies.
   2. Feeds a structured prompt to an LLM (real OpenAI if `OPENAI_API_KEY`
      is set; else a deterministic fake-LLM for offline tests).
   3. Returns a Pydantic `FundamentalsView` with fields
      `{ticker, valuation_view, key_risks, data_quality_note}`.

2. `orchestrator.build_graph()` builds a 1-node LangGraph that runs
   `FundamentalsAnalyst` and yields the view.

3. Demo: `python examples/run_fundamentals.py 000001`.

## What is intentionally a stub

Five role agents raise `NotImplementedError` with a `TODO(parity)` marker.
Grep `TODO|NotImplementedError` to see all of them. They are placeholders
so the orchestration shape is visible without committing to a v0.2.5
parity implementation today.

## Setup

```bash
cd ashare-agents
python -m venv .venv && source .venv/bin/activate
pip install -e .      # pulls ashare-mcp from GitHub (git URL dependency)
cp .env.example .env  # then fill OPENAI_API_KEY if you want real LLM calls
pytest tests/         # offline test uses fake LLM
python examples/run_fundamentals.py 000001
```

Local development against a sibling checkout of
[`ashare-mcp`](https://github.com/yli769227-jpg/ashare-mcp):

```bash
pip install -e ../ashare-mcp -e .
```

## Why split it out?

`ashare-mcp` is a stable tool layer that any agent framework can consume.
`ashare-agents` is the LangGraph-specific orchestration layer. Keeping
them in separate repos means:

- Data tool versioning is independent of orchestration churn.
- A future LangChain-free orchestrator can reuse `ashare-mcp` directly.
- Tool failures debug in `ashare-mcp`'s test suite, not here.
