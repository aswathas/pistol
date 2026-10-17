"""Smoke tests for the pistol MCP server."""

from __future__ import annotations

import asyncio

from pistol.tools import TOOL_REGISTRY, claude_tool_schema


def test_registry_size():
    assert len(TOOL_REGISTRY) == 15


def test_server_module_imports():
    from pistol_mcp import server
    assert hasattr(server, "mcp")
    from mcp.server.fastmcp import FastMCP
    assert isinstance(server.mcp, FastMCP)


def test_server_has_all_tools():
    from pistol_mcp.server import mcp
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == set(TOOL_REGISTRY.keys())


def test_schema_matches_registry():
    schemas = claude_tool_schema(TOOL_REGISTRY)
    assert len(schemas) == 15
    for s in schemas:
        assert s["name"] in TOOL_REGISTRY
        assert "input_schema" in s
