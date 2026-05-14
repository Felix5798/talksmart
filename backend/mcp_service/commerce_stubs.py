"""Stub implementations for order / logistics / human escalation.

MCP tools (`commerce_mcp`) and knowledge fallback may use these stubs.
"""

from __future__ import annotations


async def stub_order_query(*, order_id: str | None = None, uid: str | None = None) -> dict:
    return {
        "mock": True,
        "message": "[stub] 订单查询占位：未接入 OMS。",
        "order_id": order_id,
        "uid": uid,
        "sample": {"status": "paid", "amount": "¥199.00"},
    }


async def stub_logistics_query(*, tracking_no: str | None = None, order_id: str | None = None) -> dict:
    return {
        "mock": True,
        "message": "[stub] 物流查询占位：未接入 TMS。",
        "tracking_no": tracking_no,
        "order_id": order_id,
        "sample": {"status": "in_transit", "eta": "2 天内送达"},
    }


async def stub_human_handoff(*, reason: str | None = None, uid: str | None = None) -> dict:
    return {
        "mock": True,
        "message": "[stub] 已记录转人工请求（未接工单系统）。",
        "reason": reason,
        "uid": uid,
        "ticket_id": "TICKET-STUB-0001",
    }


async def stub_kb_answer(*, question: str, history_snippet: str = "") -> str:
    _ = history_snippet
    return (
        "[stub] 知识库占位回答。\n"
        f"您的问题摘要：{question[:200]!r}\n"
        "正式环境将走 RAG（检索 + 重排 + 引用）。"
    )
