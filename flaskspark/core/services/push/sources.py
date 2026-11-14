"""Topics a module serves on demand: instead of a plain NATS subscription the push service asks the module's
TopicSource, e.g. data that a service of the module only sends while someone leases it (and LINGER seconds longer
after the last tab left, so a reloaded page finds it running). The modules bring their sources in their manifests
(Module.push_sources(nc)); the push service knows none of them.

A source decides for its topics:
- handles(topic): the topic is one of its own (the first source that handles a topic serves it);
- valid(topic): it can serve it (a topic it handles but can't serve is refused like one the user may not have);
- subscribe(topic, on_update, on_last) / unsubscribe(handle): start and end it; on_last gives the latest update there
  is to the first tab at once (e.g. from the service's cache), unless a live update came first;
- max_age(topic): how long its latest update is still given to a tab that subscribes later (None: always);
- close(): the push service stops.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

Update = Callable[[dict], Awaitable[None]]


class TopicSource(ABC):
    @abstractmethod
    def handles(self, topic: str) -> bool:
        """Is `topic` one of its topics?"""

    def valid(self, topic: str) -> bool:
        """Can it serve this topic of its own? A topic it handles but can't serve is refused."""
        return True

    @abstractmethod
    async def subscribe(self, topic: str, on_update: Update, on_last: Update) -> object:
        """Start the topic (on_update: every update; on_last: the latest one there is, for the first tab); the handle
        for unsubscribe(). A failure to start is its own business (e.g. retried in the background)."""

    @abstractmethod
    async def unsubscribe(self, handle: object) -> None:
        """No tab wants the topic any more (after LINGER)."""

    def max_age(self, topic: str) -> float | None:
        """Seconds its latest update is still given to a new tab (None: always)."""
        return None

    async def close(self) -> None:
        """The push service stops."""
