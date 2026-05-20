"""
Test the orchestrator with a fake history_fn + FakeLLM so the test is 100%
offline and deterministic. Verifies:
  1. build_graph() returns a compiled graph.
  2. The graph invokes FundamentalsAnalyst with the right ticker.
  3. The output FundamentalsView has the expected schema and content.
"""
from __future__ import annotations

import os

from ashare_agents.analysts import FakeLLM, FundamentalsAnalyst, FundamentalsView
from ashare_agents.orchestrator import build_graph, run


def _fake_history(stock_code: str, years: int = 5):
    """Mirror the shape of ashare_mcp.history.track_company_history_impl."""
    assert isinstance(stock_code, str)
    return {
        "stock_code": "SZ000001",
        "company_name": "平安银行",
        "industry": "bank",
        "years": [2020, 2021, 2022, 2023, 2024],
        "report_dates": [f"{y}-12-31" for y in (2020, 2021, 2022, 2023, 2024)],
        "missing_years": [],
        "series": {
            "TOTAL_OPERATE_INCOME": [1.5e11, 1.7e11, 1.8e11, 1.85e11, 1.95e11],
            "PARENT_NETPROFIT":      [2.8e10, 3.6e10, 4.5e10, 4.6e10, 4.8e10],
            "NETCASH_OPERATE":       [1.0e10, 1.3e10, 1.4e10, 1.5e10, 1.6e10],
        },
        "fallbacks": {"TOTAL_OPERATE_INCOME": "OPERATE_INCOME"},
        "yoy": {},
        "cagr": {
            "TOTAL_OPERATE_INCOME": 0.0681,
            "PARENT_NETPROFIT": 0.1442,
        },
        "stats": {
            "TOTAL_OPERATE_INCOME": {"mean": 1.8e11, "std": 1.6e10, "trend": "up"},
            "PARENT_NETPROFIT":      {"mean": 4.0e10, "std": 7e9,    "trend": "up"},
            "NETCASH_OPERATE":       {"mean": 1.36e10, "std": 2.4e9, "trend": "up"},
        },
        "anomalies": [
            {"year": 2022, "metric": "PARENT_NETPROFIT", "yoy": 0.25, "note": "突变上升"},
        ],
    }


def test_build_graph_returns_compiled(monkeypatch):
    monkeypatch.setenv("ASHARE_AGENTS_FAKE_LLM", "1")
    analyst = FundamentalsAnalyst(
        llm=FakeLLM(default_ticker="SZ000001"),
        history_fn=_fake_history,
    )
    g = build_graph(analyst=analyst)
    # compile() returns a CompiledStateGraph that supports invoke
    assert hasattr(g, "invoke")


def test_orchestrator_fundamentals_happy_path(monkeypatch):
    monkeypatch.setenv("ASHARE_AGENTS_FAKE_LLM", "1")

    analyst = FundamentalsAnalyst(
        llm=FakeLLM(default_ticker="SZ000001"),
        history_fn=_fake_history,
    )
    out = run("000001", analyst=analyst)

    # state should carry a fundamentals view
    view = out.get("fundamentals")
    assert view is not None, f"expected fundamentals key, got {out!r}"
    assert isinstance(view, FundamentalsView)

    # ticker is forced from history result, not from LLM
    assert view.ticker == "SZ000001"
    # FakeLLM detects '"trend": "up"' in prompt → bullish
    assert view.valuation_view == "bullish"
    # at least one risk bullet
    assert isinstance(view.key_risks, list) and len(view.key_risks) >= 1
    assert isinstance(view.data_quality_note, str) and view.data_quality_note


def test_orchestrator_handles_history_failure(monkeypatch):
    """If history_fn raises, the graph should surface error rather than crash."""
    monkeypatch.setenv("ASHARE_AGENTS_FAKE_LLM", "1")

    def _broken(*_a, **_kw):
        raise RuntimeError("akshare timed out")

    analyst = FundamentalsAnalyst(
        llm=FakeLLM(default_ticker="X"),
        history_fn=_broken,
    )
    out = run("000001", analyst=analyst)
    assert out.get("fundamentals") is None
    assert "RuntimeError" in (out.get("error") or "")
