"""Chainlit UI to browse remote Chroma collections.

Run from backend/:

    chainlit run ui/chroma_viewer.py

Or:

    python run/run_chroma_ui.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import chainlit as cl

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import get_settings
from kb.vector_store import create_chroma_client


@cl.data_layer
def _no_data_layer():
    """禁用 Chainlit 持久化，避免误用 .env 中的 MySQL DATABASE_URL。"""
    return None


def _group_records(
    ids: list[str],
    documents: list[str | None],
    metadatas: list[dict | None],
) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for chunk_id, doc, meta in zip(ids, documents, metadatas):
        meta = meta or {}
        doc_id = str(meta.get("doc_id", "unknown"))
        groups[doc_id].append(
            {
                "id": chunk_id,
                "text": doc or "",
                "title": meta.get("title", ""),
                "section": meta.get("section", ""),
                "chunk_index": meta.get("chunk_index", ""),
                "doc_type": meta.get("doc_type", ""),
            }
        )
    for items in groups.values():
        items.sort(key=lambda x: (x.get("chunk_index") if x.get("chunk_index") != "" else 0))
    return dict(sorted(groups.items()))


async def _render_overview() -> None:
    settings = get_settings()
    client = create_chroma_client(settings)

    try:
        collection = client.get_collection(settings.chroma_collection)
    except Exception as exc:
        await cl.Message(
            content=(
                f"无法打开集合 `{settings.chroma_collection}`\n\n"
                f"Chroma: `{settings.chroma_url}`\n\n"
                f"错误: {exc}"
            )
        ).send()
        return

    count = collection.count()
    await cl.Message(
        content=(
            f"**Chroma** `{settings.chroma_url}`  \n"
            f"**Collection** `{settings.chroma_collection}`  \n"
            f"**向量条数** {count}"
        )
    ).send()

    if count == 0:
        await cl.Message(content="集合为空，请先运行 `python run/run_kb_pipeline.py` 入库。").send()
        return

    data = collection.get(include=["documents", "metadatas"])
    groups = _group_records(
        ids=data.get("ids") or [],
        documents=data.get("documents") or [],
        metadatas=data.get("metadatas") or [],
    )

    for doc_id, chunks in groups.items():
        title = chunks[0].get("title") or doc_id
        doc_type = chunks[0].get("doc_type") or ""
        header = f"### {title} (`{doc_id}`)"
        if doc_type:
            header += f" · {doc_type}"
        header += f"\n共 **{len(chunks)}** 个 chunk"
        await cl.Message(content=header).send()

        for chunk in chunks:
            section = chunk.get("section") or "—"
            idx = chunk.get("chunk_index", "—")
            body = (
                f"**chunk {idx}** · section: {section}  \n"
                f"`{chunk['id']}`\n\n"
                f"{chunk['text']}"
            )
            await cl.Message(content=body).send()


@cl.on_chat_start
async def on_chat_start() -> None:
    await cl.Message(
        content="正在加载 Chroma 数据…\n\n输入 `doc_id`（如 `return_policy`）可只查看该文档；输入 `refresh` 重新加载。"
    ).send()
    await _render_overview()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    query = (message.content or "").strip()
    if not query:
        return

    if query.lower() == "refresh":
        await _render_overview()
        return

    settings = get_settings()
    client = create_chroma_client(settings)
    collection = client.get_collection(settings.chroma_collection)

    data = collection.get(
        where={"doc_id": query},
        include=["documents", "metadatas"],
    )
    ids = data.get("ids") or []
    if not ids:
        await cl.Message(content=f"未找到 `doc_id={query}` 的记录。").send()
        return

    groups = _group_records(
        ids=ids,
        documents=data.get("documents") or [],
        metadatas=data.get("metadatas") or [],
    )
    for doc_id, chunks in groups.items():
        title = chunks[0].get("title") or doc_id
        await cl.Message(content=f"### {title} (`{doc_id}`) · {len(chunks)} chunks").send()
        for chunk in chunks:
            await cl.Message(
                content=f"**chunk {chunk.get('chunk_index', '—')}**\n\n{chunk['text']}"
            ).send()
