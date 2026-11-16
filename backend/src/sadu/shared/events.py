"""In-process typed event bus. Handlers run after the publishing transaction commits."""

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

log = structlog.get_logger()


@dataclass(frozen=True)
class Event:
    pass


@dataclass(frozen=True)
class ObservationReceived(Event):
    observation_id: UUID


@dataclass(frozen=True)
class ObservationStatusChanged(Event):
    observation_id: UUID
    status: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class FindingPublished(Event):
    finding_id: UUID
    facade_id: UUID
    observation_id: UUID


@dataclass(frozen=True)
class PassportDeleted(Event):
    passport_id: UUID


Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[Event], handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        for handler in self._handlers[type(event)]:
            try:
                await handler(event)
            except Exception:
                # One failing subscriber must not break the publisher or the others.
                log.exception("event_handler_failed", event=type(event).__name__)


bus = EventBus()
