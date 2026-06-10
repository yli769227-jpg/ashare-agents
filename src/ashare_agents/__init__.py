"""ashare-agents: orchestration layer over ashare-mcp."""
from .analysts import FundamentalsAnalyst, FundamentalsView
from .orchestrator import build_graph, run

__version__ = "0.0.1"

__all__ = [
    "run",
    "build_graph",
    "FundamentalsAnalyst",
    "FundamentalsView",
    "__version__",
]
