import asyncio


class EventBus:
    """Broadcast singleton. Agents and the manager publish events here.
    WebSocket clients subscribe to receive a per-connection asyncio.Queue
    that gets every event."""

    _instance = None

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Return a new queue that will receive every future event."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def publish(self, event: dict) -> None:
        """Broadcast an event to all subscribers (sync, safe from async context)."""
        for q in self._subscribers:
            q.put_nowait(event)

    @classmethod
    def get(cls) -> "EventBus":
        if not cls._instance:
            cls._instance = cls()
        return cls._instance
