from __future__ import annotations

import logging

from config import Settings, get_settings
from kb.embeddings import embed_query
from kb.rerank import rerank_documents
from kb.schemas import RetrievedChunk
from kb.vector_store import VectorStore

logger = logging.getLogger(__name__)

_PREVIEW_LEN = 120

_KB_SYSTEM_WITH_CONTEXT = """你是电商智能客服。请仅根据下方「知识库摘录」回答用户问题。
要求：
- 用简短、礼貌的中文回答；
- 若摘录不足以回答，请明确说明「知识库中暂无相关规定」，不要编造；
- 若用户问题涉及具体订单或物流，提示其可提供订单号或运单号；
- 回答末尾用一行列出参考来源（文档标题与小节即可）。"""

_KB_SYSTEM_NO_CONTEXT = """你是电商智能客服。当前未检索到与用户问题相关的知识库内容。
请用简短中文礼貌说明知识库暂无相关规定，并建议用户换个说法或联系人工客服；
若涉及订单/物流，提示可提供订单号或运单号。"""


def _preview(text: str, *, max_len: int = _PREVIEW_LEN) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= max_len:
        return one_line
    return one_line[: max_len - 3] + "..."


def _log_ctx(*, conversation_id: str | None, uid: str | None) -> str:
    parts: list[str] = []
    if conversation_id:
        parts.append(f"conversation_id={conversation_id}")
    if uid:
        parts.append(f"uid={uid}")
    return " ".join(parts) if parts else "conversation_id=-"


def _log_chunk_line(
    *,
    ctx: str,
    stage: str,
    rank: int,
    chunk: RetrievedChunk,
    vector_rank: int | None = None,
    relevance_score: float | None = None,
) -> None:
    meta = chunk.metadata
    extra = []
    if vector_rank is not None:
        extra.append(f"vector_rank={vector_rank}")
    if relevance_score is not None:
        extra.append(f"rerank_score={relevance_score:.4f}")
    if chunk.distance is not None:
        extra.append(f"distance={chunk.distance:.4f}")
    suffix = (" " + " ".join(extra)) if extra else ""
    logger.info(
        "%s %s #%d id=%s doc_id=%s section=%r%s preview=%r",
        ctx,
        stage,
        rank,
        chunk.id,
        meta.get("doc_id", ""),
        meta.get("section", ""),
        suffix,
        _preview(chunk.text),
    )
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("%s %s #%d full_text=%s", ctx, stage, rank, chunk.text)


def format_kb_context(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.metadata
        title = meta.get("title", "未知文档")
        section = meta.get("section", "")
        doc_id = meta.get("doc_id", "")
        header = f"【摘录{i}】{title}"
        if section:
            header += f" / {section}"
        if doc_id:
            header += f"（doc_id={doc_id}）"
        parts.append(f"{header}\n{chunk.text}")
    return "\n\n".join(parts)


async def retrieve_for_qa(
    query: str,
    *,
    conversation_id: str | None = None,
    uid: str | None = None,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    """Vector recall (Top-K) then qwen3-rerank (Top-N)."""
    settings = settings or get_settings()
    ctx = _log_ctx(conversation_id=conversation_id, uid=uid)

    if not settings.dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY is required for retrieval")

    query = query.strip()
    if not query:
        logger.info("%s RAG skip: empty query", ctx)
        return []

    logger.info(
        "%s RAG start query=%r top_k=%d rerank_top_n=%d min_score=%.2f",
        ctx,
        query,
        settings.kb_retrieval_top_k,
        settings.kb_rerank_top_n,
        settings.kb_rerank_min_score,
    )

    query_vec = await embed_query(query, settings=settings)
    store = VectorStore(settings)
    candidates = store.similarity_search(
        query_vec,
        k=settings.kb_retrieval_top_k,
    )

    logger.info("%s Top-K recall: requested=%d returned=%d", ctx, settings.kb_retrieval_top_k, len(candidates))
    for i, chunk in enumerate(candidates):
        _log_chunk_line(ctx=ctx, stage="TopK", rank=i + 1, chunk=chunk, vector_rank=i + 1)

    if not candidates:
        logger.info("%s RAG end: no candidates from Chroma", ctx)
        return []

    try:
        ranked = await rerank_documents(
            query,
            [c.text for c in candidates],
            top_n=settings.kb_rerank_top_n,
            settings=settings,
        )
        logger.info("%s Rerank (%s): returned=%d pairs", ctx, settings.rerank_model, len(ranked))
        for rank_i, (idx, score) in enumerate(ranked, start=1):
            if idx < 0 or idx >= len(candidates):
                logger.warning("%s Rerank #%d invalid index=%d", ctx, rank_i, idx)
                continue
            _log_chunk_line(
                ctx=ctx,
                stage="Rerank",
                rank=rank_i,
                chunk=candidates[idx],
                vector_rank=idx + 1,
                relevance_score=score,
            )
    except Exception as exc:
        logger.warning("%s Rerank failed (%s), fallback to vector order", ctx, exc)
        selected = candidates[: settings.kb_rerank_top_n]
        logger.info("%s RAG final (vector fallback): count=%d", ctx, len(selected))
        for i, chunk in enumerate(selected, start=1):
            _log_chunk_line(ctx=ctx, stage="Final", rank=i, chunk=chunk, vector_rank=i)
        return selected

    selected: list[RetrievedChunk] = []
    min_score = settings.kb_rerank_min_score
    for idx, score in ranked:
        if idx < 0 or idx >= len(candidates):
            continue
        if score < min_score:
            logger.info(
                "%s Rerank filtered: index=%d score=%.4f < min_score=%.2f",
                ctx,
                idx,
                score,
                min_score,
            )
            continue
        chunk = candidates[idx].model_copy(update={"relevance_score": score})
        selected.append(chunk)
        if len(selected) >= settings.kb_rerank_top_n:
            break

    logger.info("%s RAG final (after rerank + threshold): count=%d", ctx, len(selected))
    for i, chunk in enumerate(selected, start=1):
        _log_chunk_line(
            ctx=ctx,
            stage="Final",
            rank=i,
            chunk=chunk,
            relevance_score=chunk.relevance_score,
        )

    return selected


def kb_system_prompt(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return _KB_SYSTEM_NO_CONTEXT
    return f"{_KB_SYSTEM_WITH_CONTEXT}\n\n## 知识库摘录\n\n{format_kb_context(chunks)}"


def format_llm_prompt(
    system_content: str,
    history: list[dict],
    user_text: str,
) -> str:
    sections = [f"=== system ===\n{system_content}"]
    for m in history:
        role = m.get("role", "")
        content = str(m.get("content", ""))
        sections.append(f"=== {role} ===\n{content}")
    sections.append(f"=== user ===\n{user_text}")
    return "\n\n".join(sections)


def log_llm_prompt(
    *,
    conversation_id: str | None = None,
    uid: str | None = None,
    system_content: str,
    history: list[dict],
    user_text: str,
) -> None:
    ctx = _log_ctx(conversation_id=conversation_id, uid=uid)
    full = format_llm_prompt(system_content, history, user_text)
    logger.info("%s LLM full prompt (after rerank + concat):\n%s", ctx, full)
