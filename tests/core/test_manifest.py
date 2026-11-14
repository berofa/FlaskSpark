"""What a manifest may declare beyond pages and services: EXPOSURE, counts on menu entries of other modules
(NAV_BADGES), sections of its own on «Settings» (SETTINGS) and topics served on demand (push_sources, TopicSource)."""
from __future__ import annotations

import asyncio
import json

import pytest

from flaskspark.core import config, modules
from flaskspark.core.module import INTERNAL, PUBLIC, Module, N_
from flaskspark.core.services.push import service as push
from flaskspark.core.services.push.sources import TopicSource


# --- EXPOSURE -------------------------------------------------------------------------------------------------------
def test_exposure_defaults_to_internal_and_is_checked():
    class Plain(Module):
        NAME, LABEL = "plain", N_("Plain")

    class Open(Module):
        NAME, LABEL, EXPOSURE = "open", N_("Open"), PUBLIC

    assert Plain.EXPOSURE == INTERNAL and Open.EXPOSURE == PUBLIC
    with pytest.raises(TypeError, match="EXPOSURE"):
        class Wrong(Module):
            NAME, LABEL, EXPOSURE = "wrong", N_("Wrong"), "everyone"


def test_internal_lists_the_enabled_modules_that_are_not_public():
    assert modules.internal(config.load()) == ["demo"]


# --- NAV_BADGES -----------------------------------------------------------------------------------------------------
def test_the_layout_renders_the_entry_badge_and_the_badges_of_other_modules(client):
    html = client.get("/demo/notes").get_data(as_text=True)
    # the entry's own badge first, then the NAV_BADGES on its href (each with its own area; admin: the open app)
    spans = [part.split('"')[0] for part in html.split('data-nav-badge="')[1:]]
    assert spans == ["demo-new", "demo-open", "demo-admin"]


# --- SETTINGS -------------------------------------------------------------------------------------------------------
def test_a_modules_sections_come_into_its_settings_tab_above_its_form(client):
    html = client.get("/settings").get_data(as_text=True)
    assert "data-demo-settings" in html
    assert html.index("data-demo-settings") < html.index('action="/api/settings/config/demo"')


def test_a_module_with_sections_only_gets_the_settings_link(app):
    from flaskspark.core.web import navigation

    class OnlySections(Module):
        NAME, LABEL, SETTINGS = "sections", N_("Sections"), ("demo/settings.html",)

    with app.test_request_context("/"):
        assert navigation.admin_links([OnlySections()])  # OpenAccess: everyone is an admin, there is a section


# --- push: topics served on demand ----------------------------------------------------------------------------------
class FakeSub:
    def __init__(self, nc, topic):
        self.nc, self.topic = nc, topic

    async def unsubscribe(self):
        self.nc.subs.pop(self.topic, None)


class FakeNC:
    def __init__(self):
        self.subs = {}

    async def subscribe(self, topic, cb=None):
        self.subs[topic] = cb
        return FakeSub(self, topic)


class Leases(TopicSource):
    """Serves "feed.<name>" while someone leases it; "feed.bad" it can't serve; its latest update is valid 60 s."""

    def __init__(self):
        self.started, self.ended, self.closed = [], [], False
        self.updates = {}

    def handles(self, topic):
        return topic.startswith("feed.")

    def valid(self, topic):
        return topic != "feed.bad"

    async def subscribe(self, topic, on_update, on_last):
        self.started.append(topic)
        self.updates[topic] = on_update
        await on_last({"cached": topic})
        return f"lease-{topic}"

    async def unsubscribe(self, handle):
        self.ended.append(handle)

    def max_age(self, topic):
        return 60.0

    async def close(self):
        self.closed = True


def feed_service(source) -> push.PushService:
    """The push service with one module whose source is `source` (inside the test's event loop)."""
    class Feed(Module):
        NAME, LABEL = "feed", N_("Feed")

        def push_sources(self, nc):
            return [source]

    return push.PushService(FakeNC(), manifests=[Feed()])


def received(tab) -> list:
    out = []
    while not tab.queue.empty():
        chunk = tab.queue.get_nowait()
        if chunk and chunk.startswith("data: "):
            out.append(json.loads(chunk[6:]))
    return out


def test_a_source_starts_a_topic_once_and_gives_its_latest_update():
    source = Leases()

    async def main():
        service = feed_service(source)
        first = push.Tab({"user": 1, "topics": ["feed.>"]}, "c")
        second = push.Tab({"user": 1, "topics": ["feed.>"]}, "c")
        assert await service._topics(first, "sub", ["feed.a"]) == []
        assert received(first) == [{"topic": "feed.a", "data": {"cached": "feed.a"}}]  # on_last: at once
        await source.updates["feed.a"]({"n": 1})
        assert received(first) == [{"topic": "feed.a", "data": {"n": 1}}]
        assert await service._topics(second, "sub", ["feed.a"]) == []
        assert source.started == ["feed.a"]  # one lease for both tabs
        assert received(second) == [{"topic": "feed.a", "data": {"n": 1}}]  # the latest one, it is fresh
        assert "feed.a" not in service.nc.subs  # no plain NATS subscription for it
        assert service.details() == {"tabs": 0, "topics": 1}
        await service.http.aclose()

    asyncio.run(main())


def test_a_source_refuses_what_it_cannot_serve_and_old_updates_are_not_replayed():
    source = Leases()

    async def main():
        service = feed_service(source)
        tab = push.Tab({"user": 1, "topics": ["feed.>"]}, "c")
        assert await service._topics(tab, "sub", ["feed.bad", "other.x"]) == ["feed.bad", "other.x"]
        await service._topics(tab, "sub", ["feed.a"])
        received(tab)
        received_at, data = service.latest["feed.a"]
        service.latest["feed.a"] = (received_at - 120, data)  # older than its max_age
        late = push.Tab({"user": 2, "topics": ["feed.>"]}, "d")
        await service._topics(late, "sub", ["feed.a"])
        assert received(late) == []
        await service.http.aclose()

    asyncio.run(main())


def test_a_source_ends_its_lease_after_linger_and_closes_with_the_service(monkeypatch):
    monkeypatch.setattr(push, "LINGER", 0.01)
    source = Leases()

    async def main():
        service = feed_service(source)
        tab = push.Tab({"user": 1, "topics": ["feed.>", "plain.>"]}, "c")
        await service._topics(tab, "sub", ["feed.a", "plain.x"])
        assert "plain.x" in service.nc.subs  # a plain topic: a NATS subscription
        await service._topics(tab, "unsub", ["feed.a", "plain.x"])
        await asyncio.sleep(0.05)
        assert source.ended == ["lease-feed.a"] and "feed.a" not in service.subs and "feed.a" not in service.latest
        assert "plain.x" not in service.nc.subs
        service.runner = type("Runner", (), {"cleanup": staticmethod(lambda: asyncio.sleep(0))})()
        service.tasks = []
        await service.stop()
        assert source.closed

    asyncio.run(main())


def test_a_tab_that_comes_back_within_linger_keeps_the_lease(monkeypatch):
    monkeypatch.setattr(push, "LINGER", 0.05)
    source = Leases()

    async def main():
        service = feed_service(source)
        tab = push.Tab({"user": 1, "topics": ["feed.>"]}, "c")
        await service._topics(tab, "sub", ["feed.a"])
        await service._topics(tab, "unsub", ["feed.a"])
        again = push.Tab({"user": 1, "topics": ["feed.>"]}, "c")
        await service._topics(again, "sub", ["feed.a"])
        await asyncio.sleep(0.1)
        assert source.started == ["feed.a"] and source.ended == []
        assert received(again) == [{"topic": "feed.a", "data": {"cached": "feed.a"}}]
        await service.http.aclose()

    asyncio.run(main())


def test_areas_follow_their_position():
    from flaskspark.core.module import Area
    from flaskspark.core.web.access import areas

    class First(Module):
        NAME, LABEL = "first", N_("First")
        AREAS = (Area("late", N_("Late"), position=200), Area("plain", N_("Plain")))

    class Second(Module):
        NAME, LABEL = "second", N_("Second")
        AREAS = (Area("early", N_("Early"), position=10), Area("plain2", N_("Plain 2")))

    assert list(areas([First(), Second()])) == ["early", "plain", "plain2", "late"]
