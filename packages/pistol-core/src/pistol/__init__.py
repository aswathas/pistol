"""pistol - Indian stock market data + compute engine.

Free, MIT-licensed. 110 tools across quotes, technicals, fundamentals,
patterns, signals, breadth, screeners, portfolio, alerts, and LLM reports.
"""

__version__ = "0.1.0"

from .tools import TOOL_REGISTRY, claude_tool_schema

__all__ = ["__version__", "TOOL_REGISTRY", "claude_tool_schema"]
