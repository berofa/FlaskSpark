"""A demo application on flaskspark.core in a temporary directory: config.yaml, one module «demo» with a page, a table
and a push topic, the web app in web/app, no theme of its own (FlaskSpark's «default»). The environment is prepared
before flaskspark.core is imported (its paths come from the environment)."""
from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(tempfile.mkdtemp(prefix="flaskspark-core-tests-"))
atexit.register(shutil.rmtree, ROOT, ignore_errors=True)

FILES = {
    "config.yaml": """
app:
  name: demo-app
  title: Demo
  locales: [en, de]
theme: default
auth: none
modules: [demo]
flask:
  PERMANENT_SESSION_LIFETIME: 3600
nats:
  embedded: false
demo:
  page_size: 20
  title: Notes
  archive: false
  sort: new
  quiet_from: "22:00"
  sizes: [10, 20]
  ratios: {60: 3.0}
""",
    "src/modules/__init__.py": "",
    "src/modules/demo/__init__.py": '"""Demo module."""',
    "src/modules/demo/module.py": '''
from flaskspark.core.module import Area, Module, N_, NavBadge, NavItem, PushTopic, Screen, Tile
from flaskspark.core.settings import Setting


class Demo(Module):
    NAME = "demo"
    LABEL = N_("Demo")
    AREAS = (Area("demo", N_("Demo"), N_("The demo pages"), defaults=frozenset({"Users"})),)
    CONFIG = (
        Setting("demo.page_size", N_("Notes per page"), "int", N_("How many notes a page shows"), N_("Display"),
                min=1, max=100),
        Setting("demo.title", N_("Title"), "str", group=N_("Display")),
        Setting("demo.archive", N_("Archive old notes"), "bool", services=("push",)),
        Setting("demo.sort", N_("Order"), "choice", choices=(("new", N_("Newest first")), ("old", N_("Oldest first")))),
        Setting("demo.quiet_from", N_("Quiet from"), "time", group=N_("More")),
        Setting("demo.sizes", N_("Page sizes"), "ints", group=N_("More"), min=1),
        Setting("demo.ratios", N_("Ratios"), "json", group=N_("More")),
    )
    NAVIGATION = (NavItem(N_("Demo"), N_("Notes"), "/demo/notes", "demo", icon="journal", badge="demo-new"),)
    NAV_BADGES = (NavBadge("/demo/notes", "demo-open", "demo"), NavBadge("/demo/notes", "demo-admin", "admin"))
    SETTINGS = ("demo/settings.html",)
    PAGE_SECTIONS = {"profile": ("demo/profile.html",), "screen:wall": ("demo/screen.html",)}
    SCREENS = (Screen("wall", N_("Wall"), "demo", N_("Notes on the wall"), "display", mode="dark"),
               Screen("empty", N_("Empty"), "demo", reload_at="", position=200))
    TILES = (Tile(N_("Notes"), "/demo/notes", "demo", N_("Short notes"), "journal"),)
    PUSH_TOPICS = (PushTopic("demo.state", "demo", latest=True),)
    MODELS = ("modules.demo.models",)
    TABLES = ("demo_note",)
    ACCOUNT_TYPES = ("imap", "smtp", "carddav")
    APP_ACCOUNT_TYPES = ("gitlab",)
    SHAREABLES = ("modules.demo.sharing:NoteShareable",)
    ATTACHMENT_OWNERS = ("modules.demo.sharing:NoteFiles",)
''',
    # A note is shared with roles (flaskspark.core.shares) and has files (flaskspark.core.attachments).
    "src/modules/demo/sharing.py": '''
from flaskspark.core import attachments, shares
from flaskspark.core.module import N_
from modules.demo.models import Note


class NoteShareable(shares.Shareable):
    TYPE, AREA, LABEL = "note", "demo", N_("Note")

    def owner_of(self, s, object_id):
        note = s.get(Note, object_id)
        return note.owner_id if note is not None else None

    def name_of(self, s, object_id):
        note = s.get(Note, object_id)
        return note.text if note is not None else "?"


class NoteFiles(attachments.AttachmentOwner):
    TYPE, AREA, SHAREABLE = "note", "demo", "note"
''',
    "src/modules/demo/models.py": '''
from flaskspark.core.db import Integer, Mapped, Model, String, mapped_column


class Note(Model):
    __tablename__ = "demo_note"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    owner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
''',
    "src/modules/demo/web/__init__.py": "",
    "src/modules/demo/web/views/__init__.py": "",
    "src/modules/demo/web/views/notes.py": '''
from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import db
from modules.demo.models import Note


class NotesView(FlaskSparkMethodView):
    url = "/demo/notes"
    endpoint = "demo_notes"
    area = "demo"

    def get(self):
        with db.for_module("demo").session() as s:
            notes = [n.text for n in s.scalars(db.select(Note))]
        return render_template("demo/notes.html", notes=notes)
''',
    "src/modules/demo/web/templates/demo/notes.html": '''{% extends "layouts/main.html" %}
{% block page_title %}Notes{% endblock %}
{% block content %}<div class="app-page-head"><div><h1>Notes</h1></div></div>{% for n in notes %}<p>{{ n }}</p>{% endfor %}{% endblock %}
''',
    "src/modules/demo/web/templates/demo/settings.html": '''<section data-demo-settings>Demo section</section>
''',
    "src/modules/demo/web/templates/demo/screen.html": '''{% if can("demo") %}<section class="app-screen-section" data-demo-screen>
<ui-button data-demo-button>Edit</ui-button><span data-screen-keep>kept</span></section>{% endif %}
''',
    "src/modules/demo/web/templates/demo/profile.html": '''<section data-demo-profile>Demo profile section</section>
''',
    "web/app/__init__.py": '''
from flaskspark.core.web.app import create

flask_spark_instance, app = create("app")
''',
    "web/app/views/__init__.py": "",
    # The app's own catalogue: a text of its module, and one of the core's texts it translates differently (the app's
    # catalogue wins over the core's, flaskspark/core/locales).
    "web/app/locales/de/LC_MESSAGES/messages.po": '''
msgid ""
msgstr ""
"Content-Type: text/plain; charset=utf-8\\n"
"Language: de\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgid "Notes"
msgstr "Notizen"

msgid "Browser default"
msgstr "Wie im Browser"

msgid "%(num)s note"
msgid_plural "%(num)s notes"
msgstr[0] "%(num)s Notiz"
msgstr[1] "%(num)s Notizen"

msgid "{n} note"
msgid_plural "{n} notes"
msgstr[0] "{n} Notiz"
msgstr[1] "{n} Notizen"
''',
    # A second web app of the same application with sign-in (auth "oauth"), built by test_access.py.
    "web/app_sso/__init__.py": "",
    "web/app_sso/views/__init__.py": "",
    # A third web app whose own view is the start page («/»): the core's start page gives way.
    "web/app_home/__init__.py": "",
    "web/app_home/views/__init__.py": "",
    "web/app_home/views/start.py": '''
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core.web import OPEN


class StartView(FlaskSparkMethodView):
    url = "/"
    endpoint = "own_start"
    area = OPEN

    def get(self):
        return "the app's own start page"
''',
}
for name, text in FILES.items():
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"))


def _compile_catalogues() -> None:
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po

    for po in ROOT.glob("web/*/locales/*/LC_MESSAGES/messages.po"):
        with po.open("rb") as source, po.with_suffix(".mo").open("wb") as target:
            write_mo(target, read_po(source))


_compile_catalogues()

os.environ["APP_PROJECT_DIR"] = str(ROOT)
os.environ["APP_STATE_DIR"] = str(ROOT / "state")
os.environ["APP_CONFIG_DIR"] = str(ROOT / "conf")
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{ROOT / 'state' / 'app.db'}"
os.environ["APP_NO_DOTENV"] = "1"
os.environ["APP_SKIP_MIGRATION_CHECK"] = "1"
os.environ.setdefault("SECRET_KEY", "test")
os.environ.pop("APP_MODULES", None)
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "web")]

_cwd = os.getcwd()
os.chdir(ROOT / "web")  # FlaskSpark resolves the app package relative to the working directory
try:
    from app import app as flask_app  # noqa: E402
finally:
    os.chdir(_cwd)
    # The other FlaskSpark tests build apps called «app» of their own: forget ours (the Flask app object stays).
    for _name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[_name]
    sys.path.remove(str(ROOT / "web"))


@pytest.fixture(scope="session")
def app():
    from flaskspark.core import db

    flask_app.config.update(TESTING=True)
    db.load_models()
    db.Model.metadata.create_all(db.engine())
    return flask_app


@pytest.fixture()
def client(app):
    client = app.test_client()
    client.environ_base["HTTP_ACCEPT_LANGUAGE"] = "en"
    return client
