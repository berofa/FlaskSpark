"""Translations: tr()/ntr() in and outside a request, the catalogues' cache, the catalogue for scripts, the JS
extractor, the language in the profile and the requester's language over NATS."""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.core.sso import client_for, sso_app

CORE_PO = Path(__file__).resolve().parents[2] / "flaskspark" / "core" / "locales"


# --- tr(), ntr(), current_language() ----------------------------------------------------------------------------------
def test_tr_outside_a_request_is_in_the_applications_language(app):
    from flaskspark.core import i18n

    assert i18n.current_language() == "en"  # the demo app: locales [en, de]
    assert i18n.tr("Settings") == "Settings"
    with i18n.using("de"):
        assert i18n.current_language() == "de"
        assert i18n.tr("Settings") == "Einstellungen"
        assert i18n.tr("Guardian: %(title)s", title="X") == "Wächter: X"
        assert i18n.ntr("%(num)s note", "%(num)s notes", 1) == "1 Notiz"
        assert i18n.ntr("%(num)s note", "%(num)s notes", 3) == "3 Notizen"
        with i18n.using(None):  # None: unchanged
            assert i18n.current_language() == "de"
    assert i18n.ntr("%(num)s note", "%(num)s notes", 3) == "3 notes"
    assert i18n.tr("") == ""


def test_tr_takes_text_positionally_so_a_placeholder_may_be_called_text(app):
    from flaskspark.core.i18n import ntr, tr

    assert tr("Said: %(text)s", text="hello") == "Said: hello"
    assert ntr("%(num)s %(text)s", "%(num)s %(text)ss", 2, text="item") == "2 items"
    with pytest.raises(TypeError):
        tr(text="positional only")  # noqa


def test_tr_in_a_request_is_in_the_visitors_language(app):
    from flaskspark.core import i18n

    with app.test_request_context("/", headers={"Accept-Language": "de"}):
        assert i18n.current_language() == "de"
        assert i18n.tr("Settings") == "Einstellungen"
        assert i18n.ntr("%(num)s note", "%(num)s notes", 2) == "2 Notizen"
        assert i18n.tr("Browser default") == "Wie im Browser"  # the app's catalogue wins over the core's
        with i18n.using("en"):  # chosen explicitly: wins over the visitor's
            assert i18n.tr("Settings") == "Settings"
    with app.test_request_context("/", headers={"Accept-Language": "en"}):
        assert i18n.tr("Settings") == "Settings"


def test_n_marks_only():
    from flaskspark.core import i18n, module

    assert i18n.N_("Notes") == "Notes" and i18n.N_ is module.N_


# --- the cache --------------------------------------------------------------------------------------------------------
def _write_catalogue(directory: Path, text: str, translation: str) -> Path:
    from babel.messages.catalog import Catalog
    from babel.messages.mofile import write_mo

    catalog = Catalog(locale="de")
    catalog.add(text, translation)
    target = directory / "de" / "LC_MESSAGES" / "messages.mo"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as out:
        write_mo(out, catalog)
    return target


def test_catalogues_are_loaded_once_per_process_and_language(app, monkeypatch):
    from flaskspark.core import i18n, modules

    i18n.reset()
    calls = []
    original = modules.locale_dirs
    monkeypatch.setattr(modules, "locale_dirs", lambda cfg: calls.append(1) or original(cfg))
    first = i18n.translations("de")
    for _ in range(50):
        assert i18n.gettext("Settings", locale="de") == "Einstellungen"
        i18n.tr("Settings")
    assert i18n.translations("de") is first
    assert len(calls) == 1  # the modules (and their catalogues) were looked up once
    i18n.reset()


def test_a_changed_mo_file_is_loaded_again(app, tmp_path, monkeypatch):
    from flaskspark.core import i18n

    i18n.reset()
    mo = _write_catalogue(tmp_path, "Hello", "Hallo")
    monkeypatch.setattr(i18n, "_dirs", (str(tmp_path),))
    assert i18n.gettext("Hello", locale="de") == "Hallo"
    _write_catalogue(tmp_path, "Hello", "Grüezi")
    stat = mo.stat()
    os.utime(mo, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert i18n.gettext("Hello", locale="de") == "Hallo"  # looked at again only after CHECK_INTERVAL
    monkeypatch.setattr(i18n, "CHECK_INTERVAL", 0.0)
    assert i18n.gettext("Hello", locale="de") == "Grüezi"
    assert i18n.catalogue(tmp_path, "de").gettext("Hello") == "Grüezi"
    assert i18n.catalogue(tmp_path, "fr") is None
    i18n.reset()


def test_the_cached_gettext_is_fast(app):
    from flaskspark.core import i18n

    i18n.reset()
    i18n.gettext("Settings", locale="de")
    started = time.perf_counter()
    for _ in range(1000):
        i18n.gettext("Settings")
        i18n.gettext("Settings", locale="de")
    assert (time.perf_counter() - started) / 2000 < 0.001  # well below a millisecond per call (was several)


# --- the catalogue for scripts ----------------------------------------------------------------------------------------
def test_the_catalogue_of_a_part_for_scripts(client):
    de = {"Accept-Language": "de"}
    data = client.get("/api/i18n/catalog?modules=app", headers=de).get_json()
    assert data["language"] == "de" and data["nplurals"] == 2 and data["plural"] == "(n != 1)"
    assert data["texts"] == {"Notes": "Notizen", "Browser default": "Wie im Browser"}
    assert data["plurals"]["{n} note"] == ["{n} Notiz", "{n} Notizen"]
    core = client.get("/api/i18n/catalog?modules=core,unknown", headers=de).get_json()
    assert core["texts"]["Settings"] == "Einstellungen"
    assert core["texts"]["Browser default"] == "Wie im Browser"  # merged like the page: the app's wins
    english = client.get("/api/i18n/catalog?modules=app", headers={"Accept-Language": "en"}).get_json()
    assert english["language"] == "en" and english["texts"] == {}

    asked = client.post("/api/i18n/catalog", json={"keys": ["Saved"], "plurals": [["{n} note", "{n} notes"],
                                                                                    ["{n} cat", "{n} cats"]]},
                        headers=de).get_json()
    assert asked["texts"] == {"Saved": "Gespeichert"}
    assert asked["plurals"] == {"{n} note": ["{n} Notiz", "{n} Notizen"], "{n} cat": ["{n} cat", "{n} cats"]}
    assert client.post("/api/i18n/catalog", json={"keys": "Saved"}).status_code == 400
    # the old endpoint is unchanged
    assert client.post("/api/i18n", json={"keys": ["Saved"]}, headers=de).get_json() == {"Saved": "Gespeichert"}


def _page_catalogue(html: str) -> dict:
    found = re.search(r'<script type="application/json" id="flaskspark-i18n">(.*?)</script>', html, re.S)
    assert found, "the layout has no catalogue"
    return json.loads(found.group(1))


def test_the_layout_brings_the_catalogue_of_the_pages_module(app, client):
    from flaskspark.core.web.views.i18n import page_parts

    html = client.get("/demo/notes", headers={"Accept-Language": "de"}).get_data(as_text=True)
    data = _page_catalogue(html)
    assert data["language"] == "de" and data["plural"] == "(n != 1)"
    assert data["texts"] == {}  # the demo module has no catalogue of its own
    home = _page_catalogue(client.get("/", headers={"Accept-Language": "de"}).get_data(as_text=True))
    assert home["language"] == "de"
    from flaskspark.core import config, modules

    manifests = modules.load(config.load())
    with app.test_request_context("/demo/notes"):
        assert page_parts(manifests) == ["demo"]
    with app.test_request_context("/settings"):
        assert page_parts(manifests) == []  # the core's own page


# --- the extractor for scripts ----------------------------------------------------------------------------------------
SCRIPT = r'''
// TRANSLATORS: the button
const a = t("Save");
const html = `<button title="${t("Delete")}" class="${on ? "x" : "y"}">${esc(t(on ? "On" : "Off"))}</button>`;
const nested = `<ul>${items.map((i) => `<li title="${t("Item {n}", { n: i })}">${t(`Plain`)}</li>`).join("")}</ul>`;
const re = /t\("not a call"\)/g, half = 4 / 2;
nt("{n} file", "{n} files", n);
nt(
  "{n} row",
  "{n} rows",
  count,
);
x.t("A member call");
function t(key, params) { return key; }
N_("Joined" + " text");
t(label || "Untitled");
t(kind === "a" ? "Alpha" : "Beta");
t(dynamic);
t(`with ${dynamic}`);
t('It\'s "quoted"\n');
const s = "t(\"inside a string\")";
/* t("in a comment") */
'''


def _extract(script: str, keywords=None, tags=("TRANSLATORS:",)):
    from babel.messages.extract import extract

    keywords = keywords or {"t": None, "nt": (1, 2), "N_": None}
    return list(extract("flaskspark.core.i18n_extract:extract_js", io.BytesIO(script.encode()), keywords, list(tags)))


def test_the_js_extractor_finds_calls_in_template_literals():
    found = _extract(SCRIPT)
    messages = [m for _line, m, _c, _ctx in found]
    assert messages == ["Save", "Delete", "On", "Off", "Item {n}", "Plain", ("{n} file", "{n} files"),
                        ("{n} row", "{n} rows"), "A member call", "Joined text", "Untitled", "Alpha", "Beta",
                        "It's \"quoted\"\n"]
    assert found[0][0] == 3 and found[0][2] == ["TRANSLATORS: the button"]
    assert [line for line, m, _c, _x in found if m == ("{n} row", "{n} rows")] == [8]


def test_babels_own_extractor_loses_these_calls():
    """Why the extractor exists: Babel's JavaScript extractor misses calls inside template literals."""
    from babel.messages.extract import extract

    keywords = {"t": None, "nt": (1, 2), "N_": None}
    babel = [m for _l, m, _c, _x in extract("javascript", io.BytesIO(SCRIPT.encode()), keywords, [],
                                            options={"parse_template_string": True})]
    assert "Delete" not in babel or "Item {n}" not in babel
    assert {"Delete", "Item {n}", "On"} <= {m for _l, m, _c, _x in _extract(SCRIPT)}


def test_the_js_extractor_through_a_babel_cfg(tmp_path):
    from babel.messages.extract import extract_from_dir
    from babel.messages.frontend import parse_mapping_cfg

    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "page.js").write_text('el.innerHTML = `<b title="${t("Hint")}">${t("Body")}</b>`;\n')
    mapping = parse_mapping_cfg(io.StringIO(
        "[extractors]\nflaskspark_js = flaskspark.core.i18n_extract:extract_js\n\n[flaskspark_js: **/static/**.js]\n"))
    found = [m for _f, _l, m, _c, _x in extract_from_dir(str(tmp_path), method_map=mapping[0],
                                                         options_map=mapping[1], keywords={"t": None})]
    assert found == ["Hint", "Body"]


def test_the_js_extractor_is_an_entry_point():
    from importlib.metadata import entry_points

    names = {e.name: e.value for e in entry_points(group="babel.extractors")}
    if "flaskspark_js" not in names:
        pytest.skip("FlaskSpark installed without its entry points (an older editable install)")
    assert names["flaskspark_js"] == "flaskspark.core.i18n_extract:extract_js"


# --- the core's catalogue ---------------------------------------------------------------------------------------------
def test_the_core_catalogues_have_no_errors():
    from babel.messages.pofile import read_po

    for po in CORE_PO.glob("*/LC_MESSAGES/messages.po"):
        with po.open("rb") as source:
            catalog = read_po(source)
        errors = [(message.id, err) for message, errs in catalog.check() for err in errs]
        assert errors == [], po
        assert not [m.id for m in catalog if m.id and "python-format" in m.flags and "python-brace-format" in m.flags]


# --- the language in the profile --------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def sso(app):
    with sso_app() as sso_app_:
        yield sso_app_


def _lang(html: str) -> str:
    return re.search(r'<html lang="([^"]+)"', html).group(1)


def _clear_language(app, who: str) -> None:
    from flaskspark.core import db
    from flaskspark.core.models import UserSetting

    with db.session() as s:
        for row in s.scalars(db.select(UserSetting).where(UserSetting.user_id == app.test_users[who],
                                                          UserSetting.key == "core.language")):
            s.delete(row)


def test_a_signed_in_users_language_is_kept_in_the_profile(sso):
    _clear_language(sso, "user")
    try:
        phone = client_for(sso, "user")
        assert _lang(phone.get("/demo/notes").get_data(as_text=True)) == "en"
        response = phone.get("/language/de?next=/demo/notes")
        assert response.status_code == 302 and response.headers["Location"].endswith("/demo/notes")
        # another device: no cookie, a browser in English; the profile wins
        laptop = client_for(sso, "user")
        html = laptop.get("/demo/notes").get_data(as_text=True)
        assert _lang(html) == "de" and 'aria-pressed="true">DE<' in html
        laptop.set_cookie("lang", "en")
        assert _lang(laptop.get("/demo/notes").get_data(as_text=True)) == "de"  # profile > cookie
        page = laptop.get("/profile").get_data(as_text=True)
        assert "data-profile-language" in page and 'value="de"' in page and "Sprache der Seiten" in page
        # «browser default» removes the choice: the cookie and the browser decide again
        laptop.get("/language/system")
        assert _lang(client_for(sso, "user").get("/demo/notes").get_data(as_text=True)) == "en"
        other = client_for(sso, "other")
        assert _lang(other.get("/demo/notes").get_data(as_text=True)) == "en"  # per user
    finally:
        _clear_language(sso, "user")


def test_without_sign_in_the_language_stays_in_the_cookie(client, app):
    from flaskspark.core import db
    from flaskspark.core.models import UserSetting

    response = client.get("/language/de?next=/")
    assert "lang=de" in response.headers["Set-Cookie"]
    assert _lang(client.get("/demo/notes").get_data(as_text=True)) == "de"
    with db.session() as s:
        assert not list(s.scalars(db.select(UserSetting).where(UserSetting.key == "core.language")))
    client.get("/language/system")
    assert _lang(client.get("/demo/notes").get_data(as_text=True)) == "en"


# --- the requester's language over NATS -------------------------------------------------------------------------------
def test_best_match_of_accept_language():
    from flaskspark.core.i18n import best_match

    assert best_match("de-CH,de;q=0.9,en;q=0.5", ["en", "de"]) == "de"
    assert best_match("fr, en;q=0.8", ["en", "de"]) == "en"
    assert best_match("en;q=0.2, de;q=0.9", ["en", "de"]) == "de"
    assert best_match("de_CH", ["de_CH", "en"]) == "de_CH"
    assert best_match("fr", ["en", "de"]) is None
    assert best_match("", ["en"]) is None and best_match(None, ["en"]) is None
    assert best_match("de;q=0", ["de"]) is None


class _FakeNats:
    is_connected = True

    def __init__(self):
        self.sent = []

    async def request(self, subject, payload, timeout=0.5, headers=None):
        self.sent.append((subject, headers))
        return SimpleNamespace(data=b'{"ok": true}')


@pytest.fixture()
def fake_bus(monkeypatch):
    from flaskspark.core import events

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    nc = _FakeNats()
    monkeypatch.setattr(events, "_loop", loop)
    monkeypatch.setattr(events, "_nc", nc)
    yield nc
    loop.call_soon_threadsafe(loop.stop)
    thread.join(2)


def test_requests_to_services_carry_the_visitors_language(app, fake_bus):
    from flaskspark.core import events

    with app.test_request_context("/", headers={"Accept-Language": "de"}):
        assert events.request("demo.rpc", {"x": 1}) == {"ok": True}
    assert fake_bus.sent[-1] == ("demo.rpc", {"Accept-Language": "de"})
    events.request("demo.rpc", {}, headers={"X-Trace": "1"})  # outside a request: the application's language
    assert fake_bus.sent[-1][1] == {"X-Trace": "1", "Accept-Language": "en"}
    events.request("demo.rpc", {}, headers={"Accept-Language": "fr"})  # named by the caller: kept
    assert fake_bus.sent[-1][1] == {"Accept-Language": "fr"}


def test_a_service_answers_in_the_requesters_language(app):
    from flaskspark.core import i18n

    class Handler:
        @i18n.with_request_language
        async def on_request(self, msg):
            await asyncio.sleep(0)
            return i18n.tr("Settings"), i18n.current_language()

    @i18n.with_request_language
    def sync_handler(msg):
        return i18n.tr("Settings")

    german = SimpleNamespace(headers={"Accept-Language": "de-CH,de;q=0.9"})
    assert asyncio.run(Handler().on_request(german)) == ("Einstellungen", "de")
    assert asyncio.run(Handler().on_request(SimpleNamespace(headers=None))) == ("Settings", "en")
    assert asyncio.run(Handler().on_request(SimpleNamespace(headers={"lang": "de"})))[0] == "Einstellungen"
    assert asyncio.run(Handler().on_request(SimpleNamespace(headers={"Accept-Language": "fr"})))[1] == "en"
    assert sync_handler(german) == "Einstellungen"
    assert i18n.current_language() == "en"  # nothing leaks out of the handler

    async def two_at_once():
        return await asyncio.gather(Handler().on_request(german),
                                    Handler().on_request(SimpleNamespace(headers={"Accept-Language": "en"})))
    assert asyncio.run(two_at_once()) == [("Einstellungen", "de"), ("Settings", "en")]
