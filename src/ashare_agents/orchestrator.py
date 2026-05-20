"""
LangGraph orchestrator — currently a single-node graph that runs
FundamentalsAnalyst and returns its FundamentalsView. The graph shape is
in place so later you can drop in researchers / trader / portfolio nodes
without restructuring.

Verified against langgraph 0.2.76 + langchain 0.3.x + pydantic 2.x.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from .analysts import FundamentalsAnalyst, FundamentalsView

logger = logging.getLogger("ashare_agents")


class AgentState(TypedDict, total=False):
    """Shared state flowing through the graph."""
    ticker: str
    fundamentals: Optional[FundamentalsView]
    error: Optional[str]


def _fundamentals_node_factory(analyst: FundamentalsAnalyst):
    """Wrap a FundamentalsAnalyst instance into a LangGraph node fn."""

    def _node(state: AgentState) -> Dict[str, Any]:
        ticker = state.get("ticker")
        if not ticker:
            logger.warning("[orchestrator] missing ticker in state")
            return {"error": "missing ticker"}
        logger.info(f"[orchestrator] running fundamentals_analyst ticker={ticker!r}")
        try:
            view = analyst.analyze(ticker)
            return {"fundamentals": view}
        except Exception as e:  # noqa: BLE001
            logger.exception(f"[orchestrator] fundamentals_analyst failed: {e}")
            return {"error": f"{type(e).__name__}: {e}"}

    return _node


def build_graph(analyst: Optional[FundamentalsAnalyst] = None):
    """
    Build & compile the LangGraph. Returns a compiled graph you can `.invoke(...)` on.

    Args:
        analyst: optional injected FundamentalsAnalyst (for testing).
                 If None, a default FundamentalsAnalyst() is constructed.

    Returns:
        A compiled langgraph.graph.state.CompiledStateGraph.
    """
    if analyst is None:
        analyst = FundamentalsAnalyst()

    graph = StateGraph(AgentState)
    graph.add_node("fundamentals_analyst", _fundamentals_node_factory(analyst))
    graph.add_edge(START, "fundamentals_analyst")
    graph.add_edge("fundamentals_analyst", END)

    compiled = graph.compile()
    logger.info("[orchestrator] graph compiled: 1 node (fundamentals_analyst)")
    return compiled


def run(ticker: str, analyst: Optional[FundamentalsAnalyst] = None) -> Dict[str, Any]:
    """Convenience: build & invoke the graph for a single ticker."""
    g = build_graph(analyst=analyst)
    return g.invoke({"ticker": ticker})
