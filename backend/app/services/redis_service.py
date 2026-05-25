import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("medintel")
SESSION_TTL = 3600 * 24


class RedisService:
    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None
        self._available: bool | None = None

    async def _ensure_client(self) -> aioredis.Redis | None:
        if self._available is False:
            return None
        try:
            if self._client is None:
                self._client = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                await self._client.ping()
            self._available = True
            return self._client
        except Exception as e:
            self._available = False
            self._client = None
            logger.warning("Redis unavailable (%s). Chat memory & status updates disabled.", e)
            return None

    async def get_session_messages(self, session_id: str) -> list[dict[str, str]]:
        client = await self._ensure_client()
        if not client:
            return []
        data = await client.get(f"chat:{session_id}")
        if data:
            return json.loads(data)
        return []

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        client = await self._ensure_client()
        if not client:
            return
        messages = await self.get_session_messages(session_id)
        msg: dict[str, Any] = {"role": role, "content": content}
        if metadata:
            msg["metadata"] = metadata
        messages.append(msg)
        await client.setex(f"chat:{session_id}", SESSION_TTL, json.dumps(messages))

    async def set_session_context(self, session_id: str, context: dict[str, Any]) -> None:
        client = await self._ensure_client()
        if not client:
            return
        await client.setex(f"ctx:{session_id}", SESSION_TTL, json.dumps(context))

    async def get_session_context(self, session_id: str) -> dict[str, Any]:
        client = await self._ensure_client()
        if not client:
            return {}
        data = await client.get(f"ctx:{session_id}")
        return json.loads(data) if data else {}

    async def set_report_status(self, report_id: int, status: str, data: dict | None = None) -> None:
        client = await self._ensure_client()
        if not client:
            return
        payload = {"status": status, **(data or {})}
        await client.setex(f"report_status:{report_id}", 3600, json.dumps(payload))
        await client.publish(f"report:{report_id}", json.dumps(payload))

    async def get_report_status(self, report_id: int) -> dict | None:
        client = await self._ensure_client()
        if not client:
            return None
        data = await client.get(f"report_status:{report_id}")
        return json.loads(data) if data else None


redis_service = RedisService()
