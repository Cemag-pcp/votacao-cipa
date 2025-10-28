import asyncio
import json
import secrets
from typing import Any, Dict

from fastapi import WebSocket

from models import VotePermit


class AuthorizationChannel:
    def __init__(self) -> None:
        self._cabins: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register_cabin(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._cabins.add(websocket)

    async def unregister_cabin(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._cabins.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        message = json.dumps(payload)
        async with self._lock:
            cabins = list(self._cabins)
        for cabin in cabins:
            try:
                await cabin.send_text(message)
            except Exception:
                await self.unregister_cabin(cabin)


class VoteAuthorizationManager:
    def __init__(self) -> None:
        self._channels: dict[int, AuthorizationChannel] = {}
        self._lock = asyncio.Lock()

    async def _get_or_create_channel(self, session_id: int) -> AuthorizationChannel:
        async with self._lock:
            channel = self._channels.get(session_id)
            if channel is None:
                channel = AuthorizationChannel()
                self._channels[session_id] = channel
            return channel

    async def register_cabin(self, session_id: int, websocket: WebSocket) -> AuthorizationChannel:
        channel = await self._get_or_create_channel(session_id)
        await channel.register_cabin(websocket)
        return channel

    async def unregister_cabin(self, session_id: int, websocket: WebSocket) -> None:
        channel = await self._get_or_create_channel(session_id)
        await channel.unregister_cabin(websocket)

    async def notify_new_permit(self, permit: VotePermit) -> None:
        channel = await self._get_or_create_channel(permit.session_id)
        await channel.broadcast(
            {
                "type": "vote_permit",
                "token": permit.token,
                "issued_at": permit.issued_at.isoformat(),
            }
        )

    def generate_token(self) -> str:
        return secrets.token_urlsafe(16)


authorization_manager = VoteAuthorizationManager()