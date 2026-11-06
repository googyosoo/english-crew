import asyncio
import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        # request_id -> List of asyncio.Queue
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        # request_id -> List of recent events (buffered history)
        self._event_history: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, request_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        async with self._lock:
            if request_id not in self._subscribers:
                self._subscribers[request_id] = []
            self._subscribers[request_id].append(queue)

            # Replay buffered past events to the newly joined subscriber
            history = self._event_history.get(request_id, [])
            for payload in history:
                queue.put_nowait(payload)

        return queue

    async def unsubscribe(self, request_id: str, queue: asyncio.Queue):
        async with self._lock:
            if request_id in self._subscribers:
                if queue in self._subscribers[request_id]:
                    self._subscribers[request_id].remove(queue)
                if not self._subscribers[request_id]:
                    del self._subscribers[request_id]

    async def publish(self, request_id: str, event_type: str, data: Any):
        payload = {
            "type": event_type,
            "data": data
        }

        async with self._lock:
            # Buffer the event for late subscribers (retain up to 50 events)
            if request_id not in self._event_history:
                self._event_history[request_id] = []
            self._event_history[request_id].append(payload)
            if len(self._event_history[request_id]) > 50:
                self._event_history[request_id].pop(0)

            queues = list(self._subscribers.get(request_id, []))

        for q in queues:
            await q.put(payload)

event_bus = EventBus()
