"""Server-Sent Events for live operational updates.

Clients fall back to ~60 s polling when the stream is unavailable and must show
"LIVE UPDATES PAUSED".
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import decode_token, token_from_request
from ..services.events import bus

router = APIRouter(prefix="/api/v1", tags=["stream"])


@router.get("/stream")
async def stream(request: Request, token: str | None = Query(default=None), db: Session = Depends(get_db)):
    # EventSource cannot set headers: accept the cookie or an explicit token query.
    raw = token or token_from_request(request)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    payload = decode_token(raw)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is not active")

    async def generator():
        queue = bus.subscribe()
        try:
            yield "retry: 5000\n\n"
            for recent in bus.recent(5):
                yield f"event: {recent['event']}\ndata: {json.dumps(recent)}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    event = json.loads(message)
                    yield f"event: {event['event']}\ndata: {message}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/status")
def stream_status() -> dict[str, Any]:
    return {"subscribers": bus.subscriber_count, "recent_events": [e["event"] for e in bus.recent(10)]}
