"""MongoDB-backed conversation store with sliding window (last N rounds). Motor async."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from config import Settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def trim_messages(messages: list[dict[str, Any]], max_turns: int) -> list[dict[str, Any]]:
    """Keep the last `max_turns` user/assistant pairs (each pair = 2 messages)."""
    cap = max_turns * 2
    if len(messages) <= cap:
        return list(messages)
    return messages[-cap:]


class ChatStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncIOMotorClient | None = None

    def _db(self) -> AsyncIOMotorDatabase:
        assert self._client is not None
        return self._client[self._settings.mongodb_db]

    def _coll(self) -> AsyncIOMotorCollection:
        return self._db()["conversations"]

    async def connect(self) -> None:
        if self._client is None:
            self._client = AsyncIOMotorClient(self._settings.mongodb_uri)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def list_conversation_ids(self, *, uid: str) -> list[dict[str, Any]]:
        await self.connect()
        cur = self._coll().find({"uid": uid}, projection={"conversation_id": 1, "updated_at": 1}).sort(
            "updated_at", -1
        )
        out: list[dict[str, Any]] = []
        async for doc in cur:
            out.append(
                {
                    "conversation_id": doc["conversation_id"],
                    "updated_at": doc.get("updated_at"),
                }
            )
        return out

    async def get_messages(self, *, uid: str, conversation_id: str) -> list[dict[str, Any]]:
        await self.connect()
        doc = await self._coll().find_one({"uid": uid, "conversation_id": conversation_id})
        if not doc:
            return []
        return list(doc.get("messages", []))

    async def append_message(
        self,
        *,
        uid: str,
        conversation_id: str,
        role: str,
        content: str,
    ) -> list[dict[str, Any]]:
        """Append one message and trim to sliding window. Returns full stored messages after trim."""
        await self.connect()
        coll = self._coll()
        now = _utcnow()
        msg = {"role": role, "content": content, "ts": now.isoformat()}
        await coll.update_one(
            {"uid": uid, "conversation_id": conversation_id},
            {
                "$push": {"messages": msg},
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now, "uid": uid, "conversation_id": conversation_id},
            },
            upsert=True,
        )
        doc = await self._coll().find_one({"uid": uid, "conversation_id": conversation_id})
        assert doc is not None
        trimmed = trim_messages(doc["messages"], self._settings.max_dialog_turns)
        if len(trimmed) != len(doc["messages"]):
            await coll.update_one(
                {"uid": uid, "conversation_id": conversation_id},
                {"$set": {"messages": trimmed, "updated_at": _utcnow()}},
            )
        return trimmed

    async def delete_conversation(self, *, uid: str, conversation_id: str) -> bool:
        await self.connect()
        res = await self._coll().delete_one({"uid": uid, "conversation_id": conversation_id})
        return res.deleted_count > 0

    async def conversation_exists(self, *, uid: str, conversation_id: str) -> bool:
        await self.connect()
        doc = await self._coll().find_one({"uid": uid, "conversation_id": conversation_id}, projection={"_id": 1})
        return doc is not None

    @staticmethod
    def new_conversation_id() -> str:
        return str(uuid4())
