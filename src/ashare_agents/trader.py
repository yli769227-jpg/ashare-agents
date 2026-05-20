"""
TraderAgent — translates the debate winner into a concrete trade plan.
Stub for v0.2.5 parity work.
"""
from __future__ import annotations

from typing import Any


class TraderAgent:
    """TODO(parity): consume bullish/bearish debate output → trade plan."""
    def decide(self, debate_output: Any) -> Any:
        raise NotImplementedError(
            "TODO(parity): TraderAgent.decide not implemented. "
            "Should take the synthesized bull/bear thesis and produce a "
            "structured trade plan (action, size, entry/exit, conviction)."
        )
