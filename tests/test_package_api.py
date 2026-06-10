"""
Verify the package exposes its public API at the top level so the README
import examples (e.g. ``from ashare_agents import run``) work directly.
"""
from __future__ import annotations


def test_readme_top_level_imports():
    # The exact import shape a README example would use.
    from ashare_agents import run  # noqa: F401
    from ashare_agents import build_graph, FundamentalsAnalyst, FundamentalsView  # noqa: F401

    import ashare_agents

    assert callable(ashare_agents.run)
    assert callable(ashare_agents.build_graph)
    assert "run" in ashare_agents.__all__
    assert "build_graph" in ashare_agents.__all__
    assert "FundamentalsAnalyst" in ashare_agents.__all__
    assert "FundamentalsView" in ashare_agents.__all__
