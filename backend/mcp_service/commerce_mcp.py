"""Commerce MCP（订单 / 物流 / 转人工）— 与 `run_mcp.py`（stdio）、`run_mcp_http.py`（8200）共用工具定义。"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_service.commerce_stubs import stub_human_handoff, stub_logistics_query, stub_order_query

# Streamable HTTP 独立进程默认监听（与 `config` 中 MCP URL 一致）
MCP_HTTP_HOST = "127.0.0.1"
MCP_HTTP_PORT = 8200

commerce_mcp = FastMCP("ecommerce-commerce", host=MCP_HTTP_HOST, port=MCP_HTTP_PORT)


@commerce_mcp.tool()
async def order_get(order_id: str | None = None, uid: str | None = None) -> dict:
    """Query order details (stub)."""
    return await stub_order_query(order_id=order_id, uid=uid)


@commerce_mcp.tool()
async def logistics_track(tracking_no: str | None = None, order_id: str | None = None) -> dict:
    """Query logistics status (stub)."""
    return await stub_logistics_query(tracking_no=tracking_no, order_id=order_id)


@commerce_mcp.tool()
async def human_escalate(reason: str | None = None, uid: str | None = None) -> dict:
    """Create human handoff ticket (stub)."""
    return await stub_human_handoff(reason=reason, uid=uid)
