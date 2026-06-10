"""
Analyst agents (TradingAgents-style).

Currently implemented:
  - FundamentalsAnalyst: pulls 5-year three-statement history from ashare-mcp
    and asks an LLM for a structured fundamentals view.

Stubs (raise NotImplementedError on purpose):
  - SentimentAnalyst
  - NewsAnalyst
  - TechnicalAnalyst
  - RiskAnalyst

Design notes:
  - Structured output via Pydantic + LangChain's with_structured_output.
  - Real LLM (ChatOpenAI) gated on OPENAI_API_KEY; absent → deterministic
    FakeLLM so unit tests are 100% offline.
  - All logging is on the `ashare_agents` logger, INFO level by default.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional, Protocol

from pydantic import BaseModel, Field

logger = logging.getLogger("ashare_agents")
if not logger.handlers:
    # Module-level default: stderr, INFO. Caller can reconfigure.
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    logger.propagate = False


# ---------------------------------------------------------------------------
# Output schema (Pydantic — works with LangChain's with_structured_output)
# ---------------------------------------------------------------------------

ValuationView = Literal["bullish", "neutral", "bearish"]


class FundamentalsView(BaseModel):
    """Structured output for FundamentalsAnalyst."""
    ticker: str = Field(..., description="A-share code (normalized form, e.g. SZ000001)")
    valuation_view: ValuationView = Field(
        ..., description="overall fundamentals stance: bullish / neutral / bearish"
    )
    key_risks: List[str] = Field(
        default_factory=list,
        description="2-5 short risk bullets — quality, leverage, growth, cash flow, anomalies",
    )
    data_quality_note: str = Field(
        ...,
        description="one-sentence note on data completeness / fallbacks / anomalies observed",
    )


# ---------------------------------------------------------------------------
# LLM abstraction
# ---------------------------------------------------------------------------

class StructuredLLM(Protocol):
    """Anything with .invoke(prompt:str) -> FundamentalsView works as an LLM."""
    def invoke(self, prompt: str) -> FundamentalsView: ...  # noqa: E704


class FakeLLM:
    """
    Deterministic fallback LLM. Inspects the prompt for trend / anomaly hints
    and emits a plausible-looking FundamentalsView. Used when OPENAI_API_KEY
    is unset or in tests.

    Heuristic (intentionally simple): count occurrences of the literal trend
    tokens 'up' / 'down' in the prompt's trend lines. Majority wins, ties → neutral.
    """

    def __init__(self, default_ticker: str = "UNKNOWN") -> None:
        self.default_ticker = default_ticker

    def invoke(self, prompt: str) -> FundamentalsView:
        logger.info(f"[FakeLLM] invoke prompt_chars={len(prompt)}")
        # Pull out the 3 trend lines and count token majority.
        trend_lines = [
            line for line in prompt.splitlines()
            if line.strip().startswith(("revenue trend", "profit  trend", "cfo     trend"))
        ]
        ups = sum(1 for ln in trend_lines if ln.strip().endswith("up"))
        downs = sum(1 for ln in trend_lines if ln.strip().endswith("down"))
        view: ValuationView
        if ups > downs:
            view = "bullish"
        elif downs > ups:
            view = "bearish"
        else:
            view = "neutral"

        risks: List[str] = []
        if "突变" in prompt:
            risks.append("YoY anomalies detected in series (see history.anomalies)")
        if "OPERATE_INCOME" in prompt and '"TOTAL_OPERATE_INCOME": "OPERATE_INCOME"' in prompt:
            risks.append("Bank-industry fallback used for revenue field")
        if not risks:
            risks = ["insufficient signal to flag specific risks (fake-LLM placeholder)"]

        return FundamentalsView(
            ticker=self.default_ticker,
            valuation_view=view,
            key_risks=risks[:5],
            data_quality_note="fake-LLM heuristic; replace with real ChatOpenAI for production",
        )


def _build_real_llm(model: str) -> StructuredLLM:
    """Wrap ChatOpenAI with with_structured_output(FundamentalsView)."""
    # Lazy import so test environments without langchain still import this module.
    from langchain_openai import ChatOpenAI

    chat = ChatOpenAI(model=model, temperature=0.0)
    structured = chat.with_structured_output(FundamentalsView)

    class _Wrapper:
        def invoke(self, prompt: str) -> FundamentalsView:
            logger.info(f"[ChatOpenAI:{model}] invoke prompt_chars={len(prompt)}")
            out = structured.invoke(prompt)
            # with_structured_output returns the Pydantic instance directly in
            # recent langchain-openai versions.
            if isinstance(out, FundamentalsView):
                return out
            # Defensive: handle dict in case of version drift.
            return FundamentalsView.model_validate(out)

    return _Wrapper()


def get_default_llm(default_ticker: str = "UNKNOWN") -> StructuredLLM:
    """
    Pick an LLM based on env:
      - ASHARE_AGENTS_FAKE_LLM=1 → FakeLLM (forced, useful for tests).
      - OPENAI_API_KEY set       → real ChatOpenAI (model from ASHARE_AGENTS_MODEL).
      - else                     → FakeLLM.
    """
    if os.environ.get("ASHARE_AGENTS_FAKE_LLM") == "1":
        logger.info("LLM mode: FakeLLM (forced via ASHARE_AGENTS_FAKE_LLM=1)")
        return FakeLLM(default_ticker=default_ticker)
    if os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("ASHARE_AGENTS_MODEL", "gpt-4o-mini")
        logger.info(f"LLM mode: ChatOpenAI model={model}")
        return _build_real_llm(model)
    logger.info("LLM mode: FakeLLM (no OPENAI_API_KEY)")
    return FakeLLM(default_ticker=default_ticker)


# ---------------------------------------------------------------------------
# FundamentalsAnalyst — the only fully-wired analyst
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are an A-share fundamentals analyst. Output STRICT JSON matching the
FundamentalsView schema (no prose around the JSON).

Ticker: {ticker}
Company: {company}
Industry: {industry}

5-year time series (most-recent year last):
years        = {years}
TOTAL_OPERATE_INCOME = {revenue}
PARENT_NETPROFIT     = {profit}
NETCASH_OPERATE      = {cfo}

YoY trends summary:
revenue trend  = {trend_revenue}
profit  trend  = {trend_profit}
cfo     trend  = {trend_cfo}

CAGR:
revenue = {cagr_revenue}
profit  = {cagr_profit}

Anomalies (|YoY| > 30%): {anomalies}
Field fallbacks used:   {fallbacks}

Decide whether the fundamentals are bullish / neutral / bearish. Cite the
strongest 2-5 risk bullets. Briefly note any data-quality caveats
(fallbacks, missing years, anomalies).
"""


class FundamentalsAnalyst:
    """
    Pull 5-year three-statement history via ashare-mcp, ask an LLM for a
    structured FundamentalsView.

    Usage:
        analyst = FundamentalsAnalyst()
        view = analyst.analyze("000001")
    """

    def __init__(
        self,
        llm: Optional[StructuredLLM] = None,
        history_fn: Optional[Any] = None,
        years: int = 5,
    ) -> None:
        # Inject history fn for testability; default to the real ashare-mcp impl.
        if history_fn is None:
            from ashare_mcp.history import track_company_history_impl
            history_fn = track_company_history_impl
        self.history_fn = history_fn
        self.years = years
        self._llm = llm

    def _get_llm(self, ticker: str) -> StructuredLLM:
        if self._llm is not None:
            return self._llm
        return get_default_llm(default_ticker=ticker)

    def analyze(self, ticker: str) -> FundamentalsView:
        logger.info(f"[FundamentalsAnalyst] start ticker={ticker!r} years={self.years}")
        history = self.history_fn(ticker, self.years)
        logger.info(
            f"[FundamentalsAnalyst] history fetched: company={history.get('company_name')!r} "
            f"industry={history.get('industry')} years={history.get('years')} "
            f"anomalies={len(history.get('anomalies', []))} "
            f"fallbacks={list((history.get('fallbacks') or {}).keys())}"
        )
        prompt = self._render_prompt(ticker, history)
        llm = self._get_llm(ticker)
        view = llm.invoke(prompt)
        # Force the ticker field to the actual ticker so the LLM can't hallucinate it.
        view = view.model_copy(update={"ticker": history.get("stock_code", ticker)})
        logger.info(
            f"[FundamentalsAnalyst] done ticker={view.ticker} "
            f"view={view.valuation_view} risks={len(view.key_risks)}"
        )
        return view

    @staticmethod
    def _render_prompt(ticker: str, history: Dict[str, Any]) -> str:
        series = history.get("series") or {}
        stats = history.get("stats") or {}
        cagr = history.get("cagr") or {}

        def _trend(metric: str) -> str:
            return (stats.get(metric) or {}).get("trend", "unknown")

        def _cagr_str(metric: str) -> str:
            v = cagr.get(metric)
            return "n/a" if v is None else f"{v:.4f}"

        return _PROMPT_TEMPLATE.format(
            ticker=ticker,
            company=history.get("company_name") or "(unknown)",
            industry=history.get("industry") or "unknown",
            years=json.dumps(history.get("years") or []),
            revenue=json.dumps(series.get("TOTAL_OPERATE_INCOME") or []),
            profit=json.dumps(series.get("PARENT_NETPROFIT") or []),
            cfo=json.dumps(series.get("NETCASH_OPERATE") or []),
            trend_revenue=_trend("TOTAL_OPERATE_INCOME"),
            trend_profit=_trend("PARENT_NETPROFIT"),
            trend_cfo=_trend("NETCASH_OPERATE"),
            cagr_revenue=_cagr_str("TOTAL_OPERATE_INCOME"),
            cagr_profit=_cagr_str("PARENT_NETPROFIT"),
            # ensure_ascii=False: the prompt is consumed by an LLM, keep Chinese
            # text (e.g. anomaly notes like "突变上升") readable instead of \uXXXX.
            anomalies=json.dumps(history.get("anomalies") or [], ensure_ascii=False),
            fallbacks=json.dumps(history.get("fallbacks") or {}),
        )


# ---------------------------------------------------------------------------
# Stubs (TODO parity with TradingAgents v0.2.5 analyst suite)
# ---------------------------------------------------------------------------

class SentimentAnalyst:
    """TODO(parity): wire to weibo / xueqiu sentiment feed."""
    def analyze(self, ticker: str) -> Any:
        raise NotImplementedError(
            "TODO(parity): SentimentAnalyst not implemented. "
            "Wire to a Chinese-language sentiment data source (weibo / xueqiu / eastmoney)."
        )


class NewsAnalyst:
    """TODO(parity): wire to news headlines + RAG over filings."""
    def analyze(self, ticker: str) -> Any:
        raise NotImplementedError(
            "TODO(parity): NewsAnalyst not implemented. "
            "Needs a Chinese news source + retrieval over recent filings."
        )


class TechnicalAnalyst:
    """TODO(parity): wire to akshare daily kline + TA indicators."""
    def analyze(self, ticker: str) -> Any:
        raise NotImplementedError(
            "TODO(parity): TechnicalAnalyst not implemented. "
            "Needs daily kline data and TA indicator library."
        )


class RiskAnalyst:
    """TODO(parity): cross-check + red-flag scan + leverage / ROE warnings."""
    def analyze(self, ticker: str) -> Any:
        raise NotImplementedError(
            "TODO(parity): RiskAnalyst not implemented. "
            "Should consume ashare_mcp.checks.run_all_checks + a red-flag scanner."
        )
