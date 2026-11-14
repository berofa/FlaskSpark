"""An installed application for the tests, without installing anything: a distribution «fsdemo» written into a
directory with its *.dist-info (entry_points.txt) next to its packages; on sys.path, importlib.metadata finds its entry
points like those of a real installation.

    fsdemo                 the app's package: config.yaml, locales/ (the app's catalogue)
    fsdemo.theme           a theme (entry point flaskspark.themes)
    fsdemo.modules.alpha   a module with a page, a table, its migrations, its catalogue; OPTIONAL_DEPENDS gamma
    fsdemo.modules.beta    a module with a table but no migrations yet (POSITION 10: before alpha)
    fsdemo.modules.needy   a module that DEPENDS on «missing», which is not installed: not loaded
"""
from __future__ import annotations

from pathlib import Path

ENTRY_POINTS = """
[flaskspark.apps]
fsdemo = fsdemo

[flaskspark.modules]
alpha = fsdemo.modules.alpha
beta = fsdemo.modules.beta
needy = fsdemo.modules.needy

[flaskspark.themes]
fsdemo = fsdemo.theme
"""

ALPHA_REVISION = "a1f0c0de0001"

FILES = {
    "fsdemo-1.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: fsdemo\nVersion: 1.0\n",
    "fsdemo-1.0.dist-info/entry_points.txt": ENTRY_POINTS,
    "fsdemo/__init__.py": "",
    "fsdemo/config.yaml": """
app:
  name: fsdemo
  title: FS Demo
  locales: [en, de]
theme: fsdemo
auth: none
nats:
  embedded: false
""",
    "fsdemo/locales/de/LC_MESSAGES/messages.po": '''
msgid ""
msgstr ""
"Content-Type: text/plain; charset=utf-8\\n"
"Language: de\\n"

msgid "Alpha"
msgstr "Alpha der App"
''',
    "fsdemo/theme/__init__.py": "",
    "fsdemo/theme/theme.yaml": "title: FS Demo\nshort_name: FS\ndefault_mode: light\n",
    "fsdemo/theme/theme.css": ":root { --app-accent: #123456; }\n",
    "fsdemo/theme/images/logo.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>",
    "fsdemo/modules/__init__.py": "",
    "fsdemo/modules/alpha/__init__.py": "",
    "fsdemo/modules/alpha/module.py": '''
from flaskspark.core.module import Area, Module, N_, NavItem


class Alpha(Module):
    NAME = "alpha"
    LABEL = N_("Alpha")
    POSITION = 20
    OPTIONAL_DEPENDS = ("gamma",)
    AREAS = (Area("alpha", N_("Alpha"), defaults=frozenset({"Users"})),)
    NAVIGATION = (NavItem(N_("Alpha"), N_("Alpha items"), "/alpha/items", "alpha"),)
    MODELS = ("fsdemo.modules.alpha.models",)
    TABLES = ("alpha_item",)
    CLI = "fsdemo.modules.alpha.cli:alpha"
''',
    # the module's commands: `<app> alpha count` like `flask --app flaskspark.core.web.app:create_app alpha count`
    "fsdemo/modules/alpha/cli.py": '''
import click
from flask import current_app

from flaskspark.core import db
from fsdemo.modules.alpha.models import Item


@click.group(help="Alpha's commands.")
def alpha():
    pass


@alpha.command("count")
@click.option("--label", default="items")
def count(label):
    with db.for_module("alpha").session() as s:
        found = len(list(s.scalars(db.select(Item))))
    click.echo(f"{current_app.name}: {found} {label}")


@alpha.command("fail")
def fail():
    raise SystemExit(3)
''',
    "fsdemo/modules/alpha/models.py": '''
from flaskspark.core.db import Integer, Mapped, Model, String, mapped_column


class Item(Model):
    __tablename__ = "alpha_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(80), nullable=False, default="")
''',
    f"fsdemo/modules/alpha/migrations/versions/{ALPHA_REVISION}_alpha_tables.py": f'''
"""alpha tables"""
from alembic import op
import sqlalchemy as sa

revision = "{ALPHA_REVISION}"
down_revision = None
branch_labels = ("alpha",)
depends_on = None


def upgrade():
    op.create_table(
        "alpha_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("alpha_item")
''',
    "fsdemo/modules/alpha/locales/de/LC_MESSAGES/messages.po": '''
msgid ""
msgstr ""
"Content-Type: text/plain; charset=utf-8\\n"
"Language: de\\n"

msgid "Alpha items"
msgstr "Alpha-Einträge"

msgid "Alpha"
msgstr "Alpha des Moduls"
''',
    "fsdemo/modules/alpha/web/__init__.py": "",
    "fsdemo/modules/alpha/web/views/__init__.py": "",
    "fsdemo/modules/alpha/web/views/items.py": '''
from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import config, db, modules
from fsdemo.modules.alpha.models import Item


class ItemsView(FlaskSparkMethodView):
    url = "/alpha/items"
    endpoint = "alpha_items"
    area = "alpha"

    def get(self):
        with db.for_module("alpha").session() as s:
            items = [i.text for i in s.scalars(db.select(Item))]
        gamma = modules.is_enabled(config.load(), "gamma")
        return render_template("alpha/items.html", items=items, gamma=gamma)
''',
    "fsdemo/modules/alpha/web/templates/alpha/items.html": '''{% extends "layouts/main.html" %}
{% block content %}<h1>{{ _("Alpha items") }}</h1><p>gamma: {{ "yes" if gamma else "no" }}</p>
{% for i in items %}<p class="item">{{ i }}</p>{% endfor %}{% endblock %}
''',
    "fsdemo/modules/beta/__init__.py": "",
    "fsdemo/modules/beta/module.py": '''
from flaskspark.core.module import Module, N_


class Beta(Module):
    NAME = "beta"
    LABEL = N_("Beta")
    POSITION = 10
    MODELS = ("fsdemo.modules.beta.models",)
    TABLES = ("beta_note",)
''',
    "fsdemo/modules/beta/models.py": '''
from flaskspark.core.db import Integer, Mapped, Model, String, mapped_column


class Note(Model):
    __tablename__ = "beta_note"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(40), nullable=False, default="")
''',
    "fsdemo/modules/needy/__init__.py": "",
    "fsdemo/modules/needy/module.py": '''
from flaskspark.core.module import Module, N_


class Needy(Module):
    NAME = "needy"
    LABEL = N_("Needy")
    DEPENDS = ("missing",)
''',
    "fsdemo/modules/needy/web/__init__.py": "",
    "fsdemo/modules/needy/web/views/__init__.py": "",
    "fsdemo/modules/needy/web/views/page.py": '''
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView


class NeedyView(FlaskSparkMethodView):
    url = "/needy"
    endpoint = "needy"
    area = "open"

    def get(self):
        return "needy"
''',
}


def write(site: Path) -> Path:
    """The distribution into `site` (a directory for sys.path), catalogues compiled."""
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po

    for name, text in FILES.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.lstrip("\n"))
    for po in site.rglob("messages.po"):
        with po.open("rb") as source, po.with_suffix(".mo").open("wb") as target:
            write_mo(target, read_po(source))
    return site


# --- an application whose new version no longer delivers a module ------------------------------------------------
#
#     fsgone.modules.keep    a module with a table and its migrations (it stays)
#     fsgone.modules.omega   a module with a table, its migrations, an area and a setting (it goes and comes back)
#
# deliver() rewrites the distribution's entry points: what a new version of the application delivers.

KEEP_REVISION = "c0ffee000001"
KEEP_REVISION_2 = "c0ffee000002"
OMEGA_REVISION = "0e9a00000001"
OMEGA_REVISION_2 = "0e9a00000002"


def _revision(module: str, revision: str, down: str | None, table: str, depends_on: str | None = None) -> str:
    label = f'("{module}",)' if down is None else "None"
    return f'''
"""{module}: {table}"""
from alembic import op
import sqlalchemy as sa

revision = "{revision}"
down_revision = {down!r}
branch_labels = {label}
depends_on = {depends_on!r}


def upgrade():
    op.create_table(
        "{table}",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("{table}")
'''


GONE_FILES = {
    "fsgone-1.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: fsgone\nVersion: 1.0\n",
    "fsgone/__init__.py": "",
    "fsgone/modules/__init__.py": "",
    "fsgone/modules/keep/__init__.py": "",
    "fsgone/modules/keep/module.py": '''
from flaskspark.core.module import Module, N_


class Keep(Module):
    NAME = "keep"
    LABEL = N_("Keep")
    MODELS = ("fsgone.modules.keep.models",)
    TABLES = ("keep_item", "keep_more")
''',
    "fsgone/modules/keep/models.py": '''
from flaskspark.core.db import Integer, Mapped, Model, String, mapped_column


class KeepItem(Model):
    __tablename__ = "keep_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(80), nullable=False, default="")
''',
    f"fsgone/modules/keep/migrations/versions/{KEEP_REVISION}_keep.py": _revision("keep", KEEP_REVISION, None,
                                                                                 "keep_item"),
    "fsgone/modules/omega/__init__.py": "",
    "fsgone/modules/omega/module.py": '''
from flaskspark.core.module import Area, Module, N_
from flaskspark.core.settings import Setting


class Omega(Module):
    NAME = "omega"
    LABEL = N_("Omega")
    AREAS = (Area("omega", N_("Omega"), defaults=frozenset({"Users"})),)
    CONFIG = (Setting("omega.limit", N_("Limit"), "int"),)
    MODELS = ("fsgone.modules.omega.models",)
    TABLES = ("omega_entry", "omega_more")
''',
    "fsgone/modules/omega/models.py": '''
from flaskspark.core.db import Integer, Mapped, Model, String, mapped_column


class Entry(Model):
    __tablename__ = "omega_entry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(80), nullable=False, default="")
''',
    f"fsgone/modules/omega/migrations/versions/{OMEGA_REVISION}_omega.py": _revision("omega", OMEGA_REVISION, None,
                                                                                    "omega_entry"),
}


def deliver(site: Path, *names: str) -> None:
    """The entry points of the distribution «fsgone»: it delivers the modules `names` (a new version of it)."""
    import importlib

    lines = ["[flaskspark.modules]", *(f"{n} = fsgone.modules.{n}" for n in names)]
    (site / "fsgone-1.0.dist-info" / "entry_points.txt").write_text("\n".join(lines) + "\n")
    importlib.invalidate_caches()


def add_revision(site: Path, module: str, revision: str, down: str, table: str, depends_on: str | None = None) -> None:
    """A later revision of a module of «fsgone» (its next version); depends_on: a revision of another module it needs
    first (e.g. a foreign key to its table)."""
    path = site / "fsgone" / "modules" / module / "migrations" / "versions" / f"{revision}_{table}.py"
    path.write_text(_revision(module, revision, down, table, depends_on).lstrip("\n"))


def write_gone(site: Path) -> Path:
    """The distribution «fsgone» into `site`, delivering keep and omega."""
    for name, text in GONE_FILES.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.lstrip("\n"))
    deliver(site, "keep", "omega")
    return site
