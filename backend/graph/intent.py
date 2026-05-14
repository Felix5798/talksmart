"""Lightweight intent routing (keyword). Replace with LLM classifier later."""

from __future__ import annotations

import re


def route_intent(text: str) -> str:
    t = text.strip().lower()
    if re.search(r"人工|转人工|客服|投诉", t):
        return "human"
    if re.search(r"物流|快递|发货|配送|揽收|轨迹", t):
        return "logistics"
    if re.search(r"订单|单号|退款进度|支付", t):
        return "order"
    return "knowledge"
