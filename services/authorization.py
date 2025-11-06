import asyncio
import json
import secrets
from typing import Any, Dict, Optional

from fastapi import WebSocket

from models import VotePermit
from datetime import timezone

class AuthorizationChannel:
    def __init__(self) -> None:
        self._cabins: set[WebSocket] = set()
        self._mesarios: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def register_cabin(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._cabins.add(websocket)

    async def unregister_cabin(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._cabins.discard(websocket)

    async def register_mesario(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._mesarios.add(websocket)

    async def unregister_mesario(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._mesarios.discard(websocket)

    async def broadcast_to_cabins(self, payload: Dict[str, Any]) -> None:
        message = json.dumps(payload)
        async with self._lock:
            cabins = list(self._cabins)
        for cabin in cabins:
            try:
                await cabin.send_text(message)
            except Exception:
                await self.unregister_cabin(cabin)

    async def broadcast_to_mesarios(self, payload: Dict[str, Any]) -> None:
        message = json.dumps(payload)
        async with self._lock:
            mesarios = list(self._mesarios)
        for mesario in mesarios:
            try:
                await mesario.send_text(message)
            except Exception:
                await self.unregister_mesario(mesario)


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

    async def register_mesario(self, session_id: int, websocket: WebSocket) -> AuthorizationChannel:
        channel = await self._get_or_create_channel(session_id)
        await channel.register_mesario(websocket)
        return channel

    async def unregister_mesario(self, session_id: int, websocket: WebSocket) -> None:
        channel = await self._get_or_create_channel(session_id)
        await channel.unregister_mesario(websocket)

    async def notify_new_permit(self, permit: VotePermit) -> None:
        channel = await self._get_or_create_channel(permit.session_id)
        issued_iso = (
            permit.issued_at.replace(tzinfo=timezone.utc).isoformat()
            if permit.issued_at.tzinfo is None
            else permit.issued_at.isoformat()
        )
        await channel.broadcast_to_cabins(
            {
                "type": "vote_permit",
                "token": permit.token,
                "issued_at": issued_iso,
            }
        )

    async def notify_token_used(self, permit: VotePermit, *, candidate_id: Optional[int]) -> None:
        channel = await self._get_or_create_channel(permit.session_id)
        used_iso = None
        if getattr(permit, "used_at", None):
            used_iso = (
                permit.used_at.replace(tzinfo=timezone.utc).isoformat()
                if permit.used_at.tzinfo is None
                else permit.used_at.isoformat()
            )
        await channel.broadcast_to_mesarios(
            {
                "type": "vote_registered",
                "token": permit.token,
                "used_at": used_iso,
                "candidate_id": candidate_id,
                "null_vote": candidate_id is None,
            }
        )

    def generate_token(self) -> str:
        return secrets.token_urlsafe(16)


authorization_manager = VoteAuthorizationManager()
