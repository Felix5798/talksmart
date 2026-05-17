from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from http import HTTPStatus
from typing import Any

from config import Settings, get_settings

_RERANK_URL = "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"

_RERANK_INSTRUCT = (
    "Given a web search query, retrieve relevant passages that answer the query."
)


def _rerank_http(
    *,
    query: str,
    documents: list[str],
    top_n: int,
    api_key: str,
    model: str,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "query": query,
        "documents": documents,
        "top_n": top_n,
        "instruct": _RERANK_INSTRUCT,
    }
    req = urllib.request.Request(
        _RERANK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"rerank HTTP {exc.code}: {body}") from exc


def _parse_rerank_results(resp: Any) -> list[tuple[int, float]]:
    """Return (document_index, relevance_score) pairs, highest score first."""
    items: list[Any] | None = None

    output = getattr(resp, "output", None)
    if output is not None:
        items = getattr(output, "results", None)
        if items is None and isinstance(output, dict):
            items = output.get("results")

    if items is None:
        items = getattr(resp, "results", None)

    if items is None and isinstance(resp, dict):
        items = resp.get("results") or (resp.get("output") or {}).get("results")

    if not items:
        raise RuntimeError("rerank response missing results")

    parsed: list[tuple[int, float]] = []
    for row in items:
        if isinstance(row, dict):
            idx = int(row["index"])
            score = float(row["relevance_score"])
        else:
            idx = int(getattr(row, "index"))
            score = float(getattr(row, "relevance_score"))
        parsed.append((idx, score))

    parsed.sort(key=lambda x: x[1], reverse=True)
    return parsed


async def rerank_documents(
    query: str,
    documents: list[str],
    *,
    top_n: int | None = None,
    settings: Settings | None = None,
) -> list[tuple[int, float]]:
    """Score and rank document strings against *query* using qwen3-rerank."""
    if not documents:
        return []

    settings = settings or get_settings()
    if not settings.dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for rerank")

    n = top_n if top_n is not None else settings.kb_rerank_top_n

    def _run() -> Any:
        try:
            import dashscope
        except ImportError as exc:
            raise RuntimeError("dashscope package is required for rerank") from exc

        if not hasattr(dashscope, "TextReRank"):
            return _rerank_http(
                query=query,
                documents=documents,
                top_n=min(n, len(documents)),
                api_key=settings.dashscope_api_key,
                model=settings.rerank_model,
            )

        dashscope.api_key = settings.dashscope_api_key
        return dashscope.TextReRank.call(
            model=settings.rerank_model,
            query=query,
            documents=documents,
            top_n=min(n, len(documents)),
            instruct=_RERANK_INSTRUCT,
        )

    resp = await asyncio.to_thread(_run)

    if isinstance(resp, dict):
        if resp.get("code"):
            raise RuntimeError(f"rerank failed: {resp.get('code')} {resp.get('message')}")
        return _parse_rerank_results(resp)

    status = getattr(resp, "status_code", None)
    if status is not None and status != HTTPStatus.OK:
        message = getattr(resp, "message", resp)
        raise RuntimeError(f"rerank failed: {message}")

    code = getattr(resp, "code", None)
    if code not in (None, "", 0, "0"):
        message = getattr(resp, "message", resp)
        raise RuntimeError(f"rerank failed: {code} {message}")

    return _parse_rerank_results(resp)
