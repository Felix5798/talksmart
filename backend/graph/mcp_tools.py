"""通过 MCP（Streamable HTTP）调订单 / 物流 / 转人工工具。

意图在 `graph.intent` 与 LangGraph 路由里完成；本模块只负责 HTTP 连到独立 MCP 进程
（默认 `http://127.0.0.1:8200/mcp`，见 `run_mcp_http.py`），`initialize` + `call_tool` 后返回 dict。"""

from __future__ import annotations

import json
from typing import Any

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, TextContent

from config import Settings, get_settings
from mcp_service.commerce_mcp import MCP_HTTP_HOST, MCP_HTTP_PORT

_DEFAULT_MCP_URL = f"http://{MCP_HTTP_HOST}:{MCP_HTTP_PORT}/mcp"


def _tool_result_to_dict(result: CallToolResult) -> dict[str, Any]:
    if result.isError:
        parts: list[str] = []
        for block in result.content:
            if isinstance(block, TextContent):
                parts.append(block.text)
        raise RuntimeError("MCP tool error: " + ("; ".join(parts) if parts else "unknown"))
    if result.structuredContent is not None:
        return dict(result.structuredContent)
    texts: list[str] = []
    for block in result.content:
        if isinstance(block, TextContent):
            texts.append(block.text)
    raw = "\n".join(texts).strip()
    if not raw:
        return {}
    try:
        out = json.loads(raw)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    return {"message": raw, "mock": True}


async def call_mcp_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """调用一个 MCP 工具，返回结果字典（供图节点拼 reply）。"""
    cfg = settings or get_settings()
    url = (cfg.mcp_streamable_http_url or "").strip() or _DEFAULT_MCP_URL
    async with httpx.AsyncClient() as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments or {})
    return _tool_result_to_dict(result)
