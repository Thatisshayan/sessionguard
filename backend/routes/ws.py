"""
backend/routes/ws.py
---------------------
WebSocket endpoint for real-time push notifications.

Clients connect to /ws/{session_id} (or /ws/global for all alerts).
Server broadcasts: new alerts, review queue updates, live run events,
job completions, new insights.

Architecture:
  - ConnectionManager holds all active WebSocket connections
  - broadcast() called from engines/workers when events fire
  - Heartbeat ping every 30s to detect dead connections

Maturity: Working Prototype
Future:   Replace in-memory manager with Redis pub/sub (V7) for multi-process.
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Optional

# FastAPI WebSocket is built-in — no external library needed
try:
    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False
    APIRouter = object  # fallback for syntax

if _HAS_FASTAPI:
    router = APIRouter(tags=["websocket"])
else:
    class router:  # type: ignore
        pass


# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Connections are keyed by session_id (or 'global' for all-sessions).
    """

    def __init__(self):
        # {scope_key: [WebSocket, ...]}
        self._connections: dict[str, list] = {}

    def _key(self, scope: str | int) -> str:
        return str(scope)

    async def connect(self, websocket, scope: str | int):
        await websocket.accept()
        key = self._key(scope)
        if key not in self._connections:
            self._connections[key] = []
        self._connections[key].append(websocket)

    def disconnect(self, websocket, scope: str | int):
        key = self._key(scope)
        if key in self._connections:
            try:
                self._connections[key].remove(websocket)
            except ValueError:
                pass
            if not self._connections[key]:
                del self._connections[key]

    async def broadcast(self, scope: str | int, message: dict):
        """Send message to all connections for this scope."""
        key     = self._key(scope)
        payload = json.dumps(message)
        dead    = []
        for ws in self._connections.get(key, []):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, scope)

    async def broadcast_global(self, message: dict):
        """Send to all global subscribers."""
        await self.broadcast("global", message)

    async def broadcast_all(self, message: dict):
        """Send to every connected client."""
        payload = json.dumps(message)
        for connections in list(self._connections.values()):
            dead = []
            for ws in connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)

    def connection_count(self) -> dict:
        return {k: len(v) for k, v in self._connections.items() if v}


# Global manager — shared across all requests
manager = ConnectionManager()


# ── Routes ────────────────────────────────────────────────────────────────────

if _HAS_FASTAPI:
    from backend.auth.service import get_current_user_from_token
    from backend.auth.access import require_session_access

    @router.websocket("/ws/{scope}")
    async def websocket_endpoint(websocket: WebSocket, scope: str):
        """
        Connect to real-time updates.

        scope = 'global'   → all alerts + all job completions
        scope = '{id}'     → events scoped to session {id}

        Message format (server → client):
            {"type": "alert|insight|job|live_event|ping", "data": {...}}
        """
        token = websocket.query_params.get("token") or websocket.headers.get("authorization")
        current_user = get_current_user_from_token(token if token and token.startswith("Bearer ") else f"Bearer {token}" if token else None)
        if not current_user:
            await websocket.close(code=4401)
            return

        if scope != "global":
            try:
                await require_session_access(int(scope), f"Bearer {token}" if token and not token.startswith("Bearer ") else token)
            except Exception:
                await websocket.close(code=4403)
                return

        await manager.connect(websocket, scope)
        try:
            # Send connection confirmation
            await websocket.send_text(json.dumps({
                "type": "connected",
                "scope": scope,
                "timestamp": time.time(),
                "message": f"Connected to scope '{scope}'",
            }))

            # Keep-alive loop — client can also send pings
            while True:
                try:
                    # Wait for client message or timeout
                    data = await asyncio.wait_for(
                        websocket.receive_text(), timeout=30.0
                    )
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": time.time(),
                        }))
                except asyncio.TimeoutError:
                    # Send server-side heartbeat
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": time.time(),
                    }))
                except Exception:
                    break

        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(websocket, scope)

    @router.get("/ws/connections")
    def ws_connections():
        """Return current WebSocket connection counts (debug/admin)."""
        return {
            "connections": manager.connection_count(),
            "total": sum(manager.connection_count().values()),
        }


# ── Push helpers (called from engines/workers) ────────────────────────────────

async def push_alert(session_id: int, alert: dict):
    """Push a new alert to session subscribers and global."""
    msg = {"type": "alert", "data": alert}
    await manager.broadcast(session_id, msg)
    await manager.broadcast_global(msg)


async def push_job_complete(job: dict):
    """Push job completion to relevant session and global."""
    msg = {"type": "job_complete", "data": job}
    if job.get("session_id"):
        await manager.broadcast(job["session_id"], msg)
    await manager.broadcast_global(msg)


async def push_job_progress(job_id: int, progress: int, stage: str, session_id: int | None = None):
    """Push job progress update to relevant session and global."""
    msg = {
        "type": "job_progress",
        "data": {
            "job_id": job_id,
            "progress": progress,
            "stage": stage,
        }
    }
    if session_id:
        await manager.broadcast(session_id, msg)
    await manager.broadcast_global(msg)


async def push_live_event(session_id: int, run_id: int, event: dict):
    """Push a live session event to session subscribers."""
    msg = {"type": "live_event", "run_id": run_id, "data": event}
    await manager.broadcast(session_id, msg)


async def push_insight(session_id: int, insight: dict):
    """Push a new insight to session and global subscribers."""
    msg = {"type": "insight", "data": insight}
    await manager.broadcast(session_id, msg)
    await manager.broadcast_global(msg)


def push_sync(coro):
    """
    Helper to push from synchronous code (engines, background workers).
    Finds the running event loop and schedules the coroutine.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        pass  # No event loop — WebSocket push silently skipped
