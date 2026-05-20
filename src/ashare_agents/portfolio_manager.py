"""
PortfolioManager — final approval gate. Stub for v0.2.5 parity work.
"""
from __future__ import annotations

from typing import Any


class PortfolioManager:
    """TODO(parity): risk / position sizing / approval over a portfolio."""
    def approve(self, trade_plan: Any) -> Any:
        raise NotImplementedError(
            "TODO(parity): PortfolioManager.approve not implemented. "
            "Should apply portfolio-level constraints (sector cap, single-name "
            "exposure, total risk budget) and approve / reject the trade plan."
        )
