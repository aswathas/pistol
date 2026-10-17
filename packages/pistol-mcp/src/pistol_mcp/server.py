"""pistol MCP server.

Exposes pistol.tools.TOOL_REGISTRY (15 functions) as MCP tools over stdio.
Each tool returns a JSON string of its ToolResult (data + chart + source).
"""

from __future__ import annotations

import inspect
from typing import Any, get_args, get_origin

from mcp.server.fastmcp import FastMCP

from pistol.tools import TOOL_REGISTRY


mcp = FastMCP("pistol", instructions=(
    "Indian stock market data + compute engine. "
    "Tools return ToolResult JSON: {tool, symbol, data, chart, source, note}. "
    "Charts are plotly figure dicts the client can render itself."
))


def _json_type(hint: Any) -> str:
    if hint is inspect.Parameter.empty:
        return "string"
    if get_origin(hint) is type(None):
        return "string"
    origin = get_origin(hint)
    if origin is list:
        return "array"
    if origin is dict:
        return "object"
    if origin is not None:
        args = [a for a in get_args(hint) if a is not type(None)]
        if args:
            return _json_type(args[0])
    if hint in (int,):
        return "integer"
    if hint in (float,):
        return "number"
    if hint in (bool,):
        return "boolean"
    return "string"


def _register(fn, name: str) -> None:
    sig = inspect.signature(fn)
    doc = (fn.__doc__ or name).strip().splitlines()[0]

    @mcp.tool(name=name, description=doc)
    def _wrapper(**kwargs) -> str:
        bound = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return fn(**bound).model_dump_json()


def _register_all() -> None:
    for name, fn in TOOL_REGISTRY.items():
        _register(fn, name)


_register_all()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
