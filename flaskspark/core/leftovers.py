"""What modules left behind that no delivered module needs any more («Settings › Data», `<app> data`).

An application delivers its modules; a new version may no longer deliver one (removed or renamed). The start goes on
(flaskspark.core.db.migrations: its revision and its tables stay), and nothing of it is ever removed by itself. Here
an admin sees what is left and removes it on purpose:

    module      a module no longer delivered (core_module_chains): its tables (with their rows), its revision in
                alembic_version and its record; removed together, so a module that comes back starts afresh
    table       a table no model of the core or of a delivered module describes (not alembic_version, not
                FlaskSpark's users and roles)
    revision    a row of alembic_version of no history and no recorded module
    setting     a stored setting (core_settings) whose path no delivered module defines any more
    area        the role x area cells (core_role_area) of an area no delivered module has any more
    user-setting  the users' personal settings (core_user_settings) of a key that belongs to a module no longer
                delivered (the key is the module's name or starts with it and one of . : - _)
    state       the state directory STATE_DIR/<name>/ of a module no longer delivered

Each item has an id "<kind>:<name>". clean() removes items: first a backup of the database (and of the state
directories it removes, removed-<stamp>.tar.gz next to the backups), then everything through the database API. It
cannot be undone except from that backup.

The modules config.yaml `modules:` leaves out are still delivered: their manifests are imported here (only here, not
at the start) for their tables, settings and areas, never their models.

The guardian's findings of a service that is gone resolve themselves at its next check; NATS keeps nothing of a
module beyond its heartbeats (TTL), so neither appears here.
"""

from __future__ import annotations

import json
import logging
import shutil
import tarfile
from pathlib import Path

from . import backup, db, modules, paths
from .db import migrations

log = logging.getLogger(__name__)

KINDS = ("module", "table", "revision", "setting", "area", "user-setting", "state")
KEY_SEPARATORS = (".", ":", "-", "_")


class LeftoverError(ValueError):
    """Ids that name nothing left over (nothing is removed then)."""


def _size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def _flask_tables() -> set[str]:
    """The tables of Flask-SQLAlchemy's models in this process (an app's own, FlaskSpark's users and roles)."""
    out: set[str] = set()
    try:
        from flask import current_app, has_app_context

        if has_app_context() and "sqlalchemy" in current_app.extensions:
            for metadata in current_app.extensions["sqlalchemy"].metadatas.values():
                out |= set(metadata.tables)
    except ImportError:  # pragma: no cover - Flask is always there with FlaskSpark
        pass
    return out


def _owns(key: str, names) -> str | None:
    """The module (of `names`) a personal setting's key belongs to, None if none."""
    for name in names:
        if key == name or any(key.startswith(name + sep) for sep in KEY_SEPARATORS):
            return name
    return None


def find(cfg, url: str | None = None) -> list[dict]:
    """Everything left over: [{id, kind, name, label, ...}] (see the module's docstring), ordered by kind."""
    from .models import RoleArea, StoredSetting, UserSetting

    url = url or db.default_url()
    delivered = modules.delivered(cfg)
    classic = migrations.classic()
    existing = set(db.table_names(url))
    out: list[dict] = []

    vanished: dict[str, dict] = {}
    still: set[str] = set()  # the recorded tables of modules still delivered (also of one left out of `modules:`)
    found = None
    if not classic:
        found = migrations.state(cfg, url)
        histories = {c.name for c in migrations.chains(cfg)}
        names = {m.NAME for m in delivered} | histories | modules.delivered_names(cfg)
        for name, entry in migrations.recorded(url).items():
            if name in names:
                still |= set(entry["tables"])
            else:
                vanished[name] = entry

    # modules no longer delivered: their tables, their revision, their record
    owned_by_vanished: set[str] = set()
    for name, entry in sorted(vanished.items()):
        tables = [t for t in entry["tables"] if t in existing]
        owned_by_vanished |= set(entry["tables"])
        revisions = (found.vanished.get(name, {}).get("revisions", []) if found is not None else [])
        out.append({"id": f"module:{name}", "kind": "module", "name": name, "label": entry["label"] or name,
                    "version": entry["version"], "seen": entry["seen"],
                    "tables": [{"name": t, "rows": db.row_count(t, url)} for t in tables],
                    "revisions": revisions})

    # tables nothing describes (not in the classic layout: its own history may have tables FlaskSpark never sees)
    if not classic:
        metadata = db.load_models(cfg)
        known = (set(metadata.tables) | {migrations.VERSION_TABLE} | set(migrations.SIGNIN_TABLES) | _flask_tables()
                 | still)
        for c in migrations.chains(cfg):
            known |= set(c.tables)
        for module in delivered:
            known |= set(module.TABLES or ()) | set(module.SHARED_TABLES or ())
        for name in sorted(existing - known - owned_by_vanished):
            out.append({"id": f"table:{name}", "kind": "table", "name": name, "label": name,
                        "rows": db.row_count(name, url)})
        for rev in found.foreign:
            out.append({"id": f"revision:{rev}", "kind": "revision", "name": rev, "label": rev})

    # the core's rows of what is gone
    paths_known = {s.path for m in delivered for s in (m.CONFIG or ())}
    areas_known = {a.key for m in delivered for a in m.AREAS}
    with db.session(db.for_module(db.CORE, url)) as s:
        if "core_settings" in existing:
            for row in s.scalars(db.select(StoredSetting).order_by(StoredSetting.path)):
                if row.path not in paths_known:
                    out.append({"id": f"setting:{row.path}", "kind": "setting", "name": row.path, "label": row.path,
                                "value": json.loads(row.value)})
        if "core_role_area" in existing:
            cells: dict[str, int] = {}
            for row in s.scalars(db.select(RoleArea)):
                if row.area not in areas_known:
                    cells[row.area] = cells.get(row.area, 0) + 1
            for area, count in sorted(cells.items()):
                out.append({"id": f"area:{area}", "kind": "area", "name": area, "label": area, "rows": count})
        if "core_user_settings" in existing and vanished:
            keys: dict[str, list] = {}
            for row in s.scalars(db.select(UserSetting)):
                owner = _owns(row.key, vanished)
                if owner is not None:
                    keys.setdefault(row.key, [owner, 0])[1] += 1
            for key, (owner, count) in sorted(keys.items()):
                out.append({"id": f"user-setting:{key}", "kind": "user-setting", "name": key, "label": key,
                            "module": owner, "rows": count})

    # state directories of modules no longer delivered
    for name in sorted(vanished):
        directory = paths.STATE_DIR / name
        if directory.is_dir() and not directory.is_symlink():
            out.append({"id": f"state:{name}", "kind": "state", "name": name, "label": str(directory),
                        "path": str(directory), "size": _size(directory)})
    return sorted(out, key=lambda item: KINDS.index(item["kind"]))


def _backup_state(directories: list[Path], cfg, stamp: str) -> Path:
    """The state directories about to be removed, whole (also what NOBACKUP keeps out of the regular backups):
    removed-<stamp>.tar.gz in the backup folder (never mirrored, never pruned)."""
    dest = backup.settings(cfg)["dir"]
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"removed-{stamp}.tar.gz"
    part = out.with_name(out.name + ".part")
    with tarfile.open(part, "w:gz") as tar:
        for directory in directories:
            tar.add(directory, arcname=(Path(paths.STATE_DIR.name) / directory.name).as_posix())
    part.replace(out)
    return out


def clean(cfg, ids: list[str], url: str | None = None) -> dict:
    """Remove the items `ids` (or every item with ["all"]) after a backup; returns {removed: [ids], backup: {db,
    state}}. Ids that name nothing left over refuse everything (LeftoverError)."""
    url = url or db.default_url()
    with migrations._lock():
        items = {item["id"]: item for item in find(cfg, url)}
        wanted = list(items) if list(ids) == ["all"] else list(dict.fromkeys(ids))
        unknown = [i for i in wanted if i not in items]
        if unknown:
            raise LeftoverError(f"not left over (or gone already): {', '.join(unknown)}")
        chosen = [items[i] for i in wanted]
        result = {"removed": [], "backup": {"db": None, "state": None}}
        if not chosen:
            return result
        stamp = backup.stamp()
        if any(item["kind"] != "state" for item in chosen):
            dest = backup.settings(cfg)["dir"]
            result["backup"]["db"] = str(backup.backup_db(dest, stamp, url))
        directories = [Path(item["path"]) for item in chosen if item["kind"] == "state"]
        if directories:
            result["backup"]["state"] = str(_backup_state(directories, cfg, stamp))

        tables = [t["name"] for item in chosen if item["kind"] == "module" for t in item["tables"]]
        tables += [item["name"] for item in chosen if item["kind"] == "table"]
        if tables:
            db.drop_tables(tables, url)
        gone = [item["name"] for item in chosen if item["kind"] == "module"]
        revisions = [r for item in chosen if item["kind"] == "module" for r in item["revisions"]]
        revisions += [item["name"] for item in chosen if item["kind"] == "revision"]
        if gone or revisions:
            migrations.forget(cfg, gone, revisions, url)
        _clean_core_rows(chosen, url)
        for directory in directories:
            shutil.rmtree(directory)
        result["removed"] = wanted
        log.warning("leftovers removed: %s (backup: %s)", ", ".join(wanted),
                    ", ".join(p for p in result["backup"].values() if p) or "none")
    return result


def _clean_core_rows(chosen: list[dict], url: str) -> None:
    from . import settings
    from .models import RoleArea, StoredSetting, UserSetting

    by_kind = {kind: [item["name"] for item in chosen if item["kind"] == kind] for kind in ("setting", "area",
                                                                                         "user-setting")}
    if not any(by_kind.values()):
        return
    with db.session(db.for_module(db.CORE, url)) as s:
        if by_kind["setting"]:
            s.execute(db.delete(StoredSetting).where(StoredSetting.path.in_(by_kind["setting"])))
        if by_kind["area"]:
            s.execute(db.delete(RoleArea).where(RoleArea.area.in_(by_kind["area"])))
        if by_kind["user-setting"]:
            s.execute(db.delete(UserSetting).where(UserSetting.key.in_(by_kind["user-setting"])))
    settings.invalidate()
