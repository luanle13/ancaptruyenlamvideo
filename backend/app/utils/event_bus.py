# AnCapTruyenLamVideo - Event Bus for SSE Broadcasting

import asyncio
from typing import Dict, Set
from collections import defaultdict
import logging

from ..models.crawler import ProgressEvent

logger = logging.getLogger(__name__)


class EventBus:
    """Manages SSE connections and event broadcasting."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        return cls._instance

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to events for a specific task."""
        queue = asyncio.Queue()
        self.subscribers[task_id].add(queue)
        logger.info(f"New subscriber for task {task_id}. Total: {len(self.subscribers[task_id])}")
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue):
        """Unsubscribe from task events."""
        self.subscribers[task_id].discard(queue)
        logger.info(f"Unsubscribed from task {task_id}. Remaining: {len(self.subscribers[task_id])}")
        if not self.subscribers[task_id]:
            del self.subscribers[task_id]

    async def publish(self, task_id: str, event: ProgressEvent):
        """Publish event to all subscribers of a task."""
        if task_id not in self.subscribers:
            return

        for queue in list(self.subscribers[task_id]):
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"Error publishing event: {e}")

    def get_subscriber_count(self, task_id: str) -> int:
        """Get number of subscribers for a task."""
        return len(self.subscribers.get(task_id, set()))


# Singleton instance
event_bus = EventBus()
