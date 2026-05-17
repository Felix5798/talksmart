from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import get_settings
from graph.chat_store import ChatStore
from graph.chatbot_graph import get_compiled_graph

_store: ChatStore | None = None


def _configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.kb_log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def store() -> ChatStore:
    global _store
    if _store is None:
        _store = ChatStore(get_settings())
    return _store


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    await store().connect()
    try:
        yield
    finally:
        global _store
        if _store is not None:
            await _store.close()
            _store = None


app = FastAPI(title="E-commerce Chatbot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    uid: str = Field(default="1001", description="User id (dev default 1001)")
    conversation_id: str | None = Field(default=None, description="Existing conversation; omit to create")
    message: str = Field(..., min_length=1)


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _chunk_text(text: str, chunk_size: int = 64) -> AsyncIterator[str]:
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


@app.post("/api/chat/stream")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    s = store()
    uid = body.uid
    conv_id = body.conversation_id or ChatStore.new_conversation_id()

    messages = await s.append_message(
        uid=uid, conversation_id=conv_id, role="user", content=body.message
    )

    graph = get_compiled_graph()
    state: dict[str, Any] = {
        "uid": uid,
        "conversation_id": conv_id,
        "user_text": body.message,
        "history": messages,
    }
    result = await graph.ainvoke(state)
    reply = str(result.get("reply") or "")

    async def gen() -> AsyncIterator[bytes]:
        yield _sse({"type": "meta", "conversation_id": conv_id, "uid": uid}).encode("utf-8")
        async for part in _chunk_text(reply):
            yield _sse({"type": "token", "text": part}).encode("utf-8")
        await s.append_message(uid=uid, conversation_id=conv_id, role="assistant", content=reply)
        yield _sse({"type": "done"}).encode("utf-8")

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/conversations")
async def list_conversations(uid: str = Query("1001")) -> dict[str, Any]:
    items = await store().list_conversation_ids(uid=uid)
    return {"uid": uid, "items": items}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, uid: str = Query("1001")) -> dict[str, Any]:
    ok = await store().delete_conversation(uid=uid, conversation_id=conversation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"ok": True, "conversation_id": conversation_id}


@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, uid: str = Query("1001")) -> dict[str, Any]:
    s = store()
    msgs = await s.get_messages(uid=uid, conversation_id=conversation_id)
    if msgs:
        return {"uid": uid, "conversation_id": conversation_id, "messages": msgs}
    if not await s.conversation_exists(uid=uid, conversation_id=conversation_id):
        raise HTTPException(status_code=404, detail="conversation not found")
    return {"uid": uid, "conversation_id": conversation_id, "messages": msgs}


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8100, reload=True)
