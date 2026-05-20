"""
Researcher agents — debate roles. Both raise NotImplementedError until we
commit to a v0.2.5 parity implementation.

Design intent:
  - BullishResearcher takes the union of analyst views and argues the bull case.
  - BearishResearcher does the opposite.
  - Their outputs feed back into the LangGraph for trader / portfolio decisions.
"""
from __future__ import annotations

from typing import Any


class BullishResearcher:
    """TODO(parity): see TradingAgents v0.2.5 researcher prompt + state machine."""
    def argue(self, analyst_views: Any) -> Any:
        raise NotImplementedError(
            "TODO(parity): BullishResearcher.argue not implemented. "
            "Should accept fundamentals/sentiment/news/technical/risk views "
            "and produce a structured bull thesis."
        )


class BearishResearcher:
    """TODO(parity): mirror of BullishResearcher."""
    def argue(self, analyst_views: Any) -> Any:
        raise NotImplementedError(
            "TODO(parity): BearishResearcher.argue not implemented. "
            "Mirror of BullishResearcher but with bear-thesis prompts."
        )
