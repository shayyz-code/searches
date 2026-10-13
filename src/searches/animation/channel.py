"""Bounded event delivery and cooperative demand/cancellation."""

from queue import Full, Queue
from threading import Condition

from searches.events import SearchEvent


class AnimationCancelled(Exception):
    """The user ended a walkthrough before its search produced a result."""


class EventChannel:
    capacity = 256

    def __init__(self):
        self.events: Queue[SearchEvent] = Queue(maxsize=self.capacity)
        self.condition = Condition()
        self.credits = 0
        self.cancelled = False
        self.waiting = False
        self.max_buffered = 0

    def grant(self, steps: int) -> None:
        with self.condition:
            self.credits = min(32, self.credits + steps)
            self.condition.notify_all()

    def cancel(self) -> None:
        with self.condition:
            self.cancelled = True
            self.condition.notify_all()

    def __call__(self, event: SearchEvent) -> None:
        while True:
            if self.cancelled:
                raise AnimationCancelled()
            try:
                self.events.put(event, timeout=0.02)
                self.max_buffered = max(self.max_buffered, self.events.qsize())
                break
            except Full:
                continue
        if event.kind in ("initialized", "expanded"):
            with self.condition:
                self.waiting = True
                while not self.cancelled and self.credits == 0:
                    self.condition.wait(0.05)
                self.waiting = False
                if self.cancelled:
                    raise AnimationCancelled()
                self.credits -= 1
