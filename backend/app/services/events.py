"""In-process pub/sub behind the SSE endpoint.

Production replaces the fan-out with Redis pub/sub; the event contract
(risk.updated, alert.created, alert.updated, report.created, assignment.updated,
feed.degraded) stays identical.
"""

from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import datetime, timezone
from typing import Any


class EventBus:
    def __init__(self, buffer: int = 100) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._history: deque[dict[str, Any]] = deque(maxlen=buffer)

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: str, payload: dict[str, Any], *, scope: str | None = None) -> None:
        envelope = {
            "event": event,
            "at": datetime.now(timezone.utc).isoformat(),
            "scope": scope,
            "payload": payload,
        }
        self._history.append(envelope)
        message = json.dumps(envelope, default=str)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                self._subscribers.discard(queue)

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._history)[-limit:]

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


bus = EventBus()
