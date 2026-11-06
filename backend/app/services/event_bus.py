import asyncio
import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        # request_id -> List of asyncio.Queue
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, request_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        async with self._lock:
            if request_id not in self._subscribers:
                self._subscribers[request_id] = []
            self._subscribers[request_id].append(queue)
        return queue

    async def unsubscribe(self, request_id: str, queue: asyncio.Queue):
        async with self._lock:
            if request_id in self._subscribers:
                if queue in self._subscribers[request_id]:
                    self._subscribers[request_id].remove(queue)
                if not self._subscribers[request_id]:
                    del self._subscribers[request_id]

    async def publish(self, request_id: str, event_type: str, data: Any):
        async with self._lock:
            queues = list(self._subscribers.get(request_id, []))

        payload = {
            "type": event_type,
            "data": data
        }
        for q in queues:
            await q.put(payload)

event_bus = EventBus()
