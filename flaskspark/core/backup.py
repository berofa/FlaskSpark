"""Backups of the application: the database and the state directory (`<app> backup`, e.g. from a systemd timer or a
cron job every 15 minutes).

Every run:
- the database: a consistent copy through the database API (flaskspark.core.db: the Database of its URL, e.g. the
  SQLite backup API, also while the services write), checked, gzipped: db-<stamp>.db.gz;
- the state directory (STATE_DIR) as state-<stamp>.tar.gz, without the database (its own copy), the backups, the
  sessions, the NATS store, temporary files and logs, and never a folder marked with a NOBACKUP file (a module marks
  what must not leave the host, e.g. keys); the same archive holds the further directories of config.yaml
  `backup.include` and of the modules (Module.backup_paths) under extra/<absolute path> (NOBACKUP, temporary files and
  logs are left out there too);
- prune: every backup of the last `keep_hours`, then the newest one per day for `keep_days`;
- mirror (with `mirror_dir`): the backup folder to a second folder (e.g. a network share with backup jobs of its own);
  files pruned locally go there too. A mirror folder that is not there (the share away) only skips the mirror.

config.yaml:

    backup:
      dir: ~/backups/myapp      # default STATE_DIR/backups
      keep_hours: 48
      keep_days: 7
      state: true               # the state directory too
      max_age_hours: 26         # the status tile warns when the latest backup is older
      mirror_dir: /mnt/share/myapp   # optional: a copy of the backup folder
      include: [/srv/myapp/files]    # optional: further directories into the archive of the state

Secrets (CONFIG_DIR/*.env, the environment) are never part of a backup: keep them separately.

    <app> backup                     one run
    <app> backup-list                the backups
    <app> backup-check <file>        integrity and rows per table of a database backup
    <app> backup-restore <file>      put a database backup in place of the live database (stop the services first)
"""

from __future__ import annotations

import gzip
import logging
import re
import shutil
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path

from . import db, paths

log = logging.getLogger(__name__)

DEFAULTS = {"dir": "", "keep_hours": 48, "keep_days": 7, "state": True, "max_age_hours": 26, "mirror_dir": "",
            "include": []}
NAME = re.compile(r"^(db|state)-(\d{8}-\d{6})\.(db\.gz|tar\.gz)$")
STAMP = "%Y%m%d-%H%M%S"
#: a folder with this file is never part of a backup; the modules mark them, the core knows no names
NOBACKUP = ".nobackup"
#: top-level entries of the state directory never backed up (regenerable or live data of other systems)
STATE_EXCLUDE = ("backups", "sessions", "nats")
STATE_EXCLUDE_SUFFIX = (".log", ".tmp", ".part", "-wal", "-shm", "-journal")


def settings(cfg) -> dict:
    out = {**DEFAULTS, **((cfg.section("backup") or {}) if cfg is not None else {})}
    out["dir"] = Path(out["dir"]).expanduser() if out["dir"] else paths.STATE_DIR / "backups"
    out["mirror_dir"] = Path(out["mirror_dir"]).expanduser() if out["mirror_dir"] else None
    include = out["include"] or []
    out["include"] = [Path(p).expanduser() for p in ([include] if isinstance(include, str) else include) if p]
    return out


def included(cfg) -> list[Path]:
    """The further paths of a backup: config.yaml `backup.include` and the loaded modules' backup_paths(), absolute,
    each once, in that order."""
    from . import modules

    found = list(settings(cfg)["include"])
    for module in modules.load(cfg) if cfg is not None else ():
        try:
            found += [Path(p).expanduser() for p in module.backup_paths(cfg) or ()]
        except Exception:  # noqa: BLE001 - one module's mistake doesn't stop the backup
            log.exception("backup: the paths of module %s", module.NAME)
    out = []
    for path in found:
        path = path.resolve()
        if path not in out:
            out.append(path)
    return out


def stamp(now: float | None = None) -> str:
    return datetime.fromtimestamp(now or time.time()).strftime(STAMP)


def verify(path: Path, url: str | None = None) -> dict:
    """Open a (gzipped) database backup: {integrity ("ok" or what is wrong), counts (rows per table)}."""
    with tempfile.TemporaryDirectory() as tmp:
        plain = Path(tmp) / "check.db"
        _unpack(Path(path), plain)
        return {"integrity": db.check(plain, url), "counts": db.counts(plain, url)}


def _unpack(path: Path, target: Path) -> None:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as src, target.open("wb") as dst:
        shutil.copyfileobj(src, dst)


def backup_db(dest: Path, stamp_: str, url: str | None = None) -> Path:
    """Consistent copy of the live database, checked, gzipped: <dest>/db-<stamp>.db.gz."""
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"db-{stamp_}.db.gz"
    with tempfile.TemporaryDirectory(dir=dest) as tmp:
        plain = Path(tmp) / "copy.db"
        db.copy(plain, url)
        integrity = db.check(plain, url)
        if integrity != "ok":
            raise RuntimeError(f"backup copy failed the integrity check: {integrity}")
        part = out.with_name(out.name + ".part")
        with plain.open("rb") as f, gzip.open(part, "wb", compresslevel=6) as g:
            shutil.copyfileobj(f, g)
        part.replace(out)
    return out


def backup_state(state_dir: Path | None, dest: Path, stamp_: str, exclude: tuple[Path, ...] = (),
                 extra: tuple[Path, ...] = ()) -> Path:
    """The state directory without what STATE_EXCLUDE, STATE_EXCLUDE_SUFFIX, NOBACKUP and `exclude` (absolute paths:
    the database, the backups) leave out, and the paths `extra` (under extra/<absolute path>; None as state_dir: only
    these): <dest>/state-<stamp>.tar.gz."""
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / f"state-{stamp_}.tar.gz"
    part = out.with_name(out.name + ".part")
    skipped = {p.resolve() for p in exclude}
    roots = []
    if state_dir is not None:
        state_dir = Path(state_dir)
        skipped |= {(state_dir / n).resolve() for n in STATE_EXCLUDE}
        roots.append((state_dir, Path(state_dir.name)))
    for path in extra:
        path = Path(path)
        if not path.exists():
            log.warning("backup: %s is not there", path)
            continue
        roots.append((path, Path("extra") / path.resolve().relative_to(path.resolve().anchor)))
    with tarfile.open(part, "w:gz") as tar:
        for root, arc_root in roots:
            marked = skipped | ({p.parent.resolve() for p in root.rglob(NOBACKUP)} if root.is_dir() else set())
            for path in [root, *(sorted(root.rglob("*")) if root.is_dir() else ())]:
                resolved = path.resolve()
                if any(resolved == s or s in resolved.parents for s in marked) or \
                        path.name.endswith(STATE_EXCLUDE_SUFFIX):
                    continue
                if path.is_symlink() and path != root:
                    continue  # never follow links out of the directory
                arcname = (arc_root / path.relative_to(root)).as_posix()
                try:
                    tar.add(path, arcname=arcname, recursive=False)
                except FileNotFoundError:
                    continue  # replaced or removed while the backup runs (atomic writes of the services)
    part.replace(out)
    return out


def backups(dest: Path) -> list[tuple[str, float, Path]]:
    """(kind, time, path) of every backup in `dest`, oldest first."""
    if not Path(dest).is_dir():
        return []
    out = []
    for p in Path(dest).iterdir():
        m = NAME.match(p.name)
        if m:
            out.append((m.group(1), datetime.strptime(m.group(2), STAMP).timestamp(), p))
    return sorted(out, key=lambda b: (b[1], b[0]))


def prune(dest: Path, keep_hours: float, keep_days: float, now: float | None = None) -> list[Path]:
    """Keep every backup of the last keep_hours, then the newest one per day for keep_days; returns the removed files."""
    now = now or time.time()
    by_kind: dict[str, list[tuple[float, Path]]] = {}
    for kind, ts, p in backups(dest):
        by_kind.setdefault(kind, []).append((ts, p))
    removed = []
    for items in by_kind.values():
        days_kept: set[str] = set()
        for ts, p in sorted(items, reverse=True):
            age = now - ts
            day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            if age <= keep_hours * 3600:
                days_kept.add(day)  # the day has its backups already
                continue
            if age <= keep_days * 86400 and day not in days_kept:
                days_kept.add(day)
                continue
            p.unlink()
            removed.append(p)
    return removed


def mirror(src: Path, dest: Path) -> tuple[int, int]:
    """Copy the backups of `src` that `dest` lacks, remove there what is gone in `src`; (copied, removed). Raises
    FileNotFoundError when `dest` is not there."""
    if not Path(dest).is_dir():
        raise FileNotFoundError(f"mirror folder not reachable: {dest}")
    local = {p.name for _, _, p in backups(src)}
    copied = removed = 0
    for name in sorted(local):
        target = Path(dest) / name
        if not target.exists():
            part = Path(dest) / f"{name}.part"
            shutil.copyfile(Path(src) / name, part)
            part.replace(target)
            copied += 1
    for _, _, p in backups(dest):
        if p.name not in local:
            p.unlink()
            removed += 1
    return copied, removed


def mirrored(s: dict) -> dict | None:
    """The mirror for the status: {ok, count, error} (ok: it has the latest database backup), None without one."""
    if s["mirror_dir"] is None:
        return None
    try:
        names = {p.name for k, _, p in backups(s["mirror_dir"]) if k == "db"} if s["mirror_dir"].is_dir() else None
    except OSError as exc:
        return {"ok": False, "count": 0, "error": str(exc)}
    if names is None:
        return {"ok": False, "count": 0, "error": f"not reachable: {s['mirror_dir']}"}
    last = latest(s["dir"])
    return {"ok": bool(last and last.name in names), "count": len(names), "error": None}


def latest(dest: Path, kind: str = "db") -> Path | None:
    found = [p for k, _, p in backups(dest) if k == kind]
    return found[-1] if found else None


def run(cfg, url: str | None = None, now: float | None = None) -> dict:
    """One backup run: database, state directory, prune."""
    s = settings(cfg)
    when = stamp(now)
    dbf = backup_db(s["dir"], when, url)
    result = {"db": str(dbf), "state": None, "pruned": 0}
    extra = tuple(included(cfg))
    state_dir = paths.STATE_DIR if s["state"] and paths.STATE_DIR.is_dir() else None
    if state_dir is not None or extra:
        live = []
        try:
            live.append(Path(db.location(url)))
        except ValueError:
            pass  # not a file (a database server)
        stf = backup_state(state_dir, s["dir"], when, exclude=(s["dir"], *live), extra=extra)
        result["state"] = str(stf)
    removed = prune(s["dir"], s["keep_hours"], s["keep_days"], now)
    result["pruned"] = len(removed)
    if s["mirror_dir"] is not None:
        try:
            copied, gone = mirror(s["dir"], s["mirror_dir"])
            result["mirror"] = {"copied": copied, "removed": gone}
        except OSError as exc:  # the share away: the local backup is there, the next run mirrors it
            log.warning("backup not mirrored: %s", exc)
            result["mirror"] = {"error": str(exc)}
    log.info("backup %s (%d kB)%s, %d old ones removed", dbf.name, dbf.stat().st_size // 1024,
             f", {Path(result['state']).name}" if result["state"] else "", len(removed))
    return result


def restore(path: Path, url: str | None = None) -> dict:
    """Put the database backup `path` in place of the live database: checked first, refused when broken. The services
    must be stopped. The live database is kept next to it (<file>.before-restore-<stamp>) when it is a file."""
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmp:
        plain = Path(tmp) / "restore.db"
        _unpack(path, plain)
        integrity = db.check(plain, url)
        if integrity != "ok":
            raise RuntimeError(f"{path.name} failed the integrity check: {integrity}")
        kept = None
        try:
            live = Path(db.location(url))
        except ValueError:
            live = None
        if live is not None and live.is_file():
            kept = live.with_name(f"{live.name}.before-restore-{stamp()}")
            db.copy(kept, url)
        target = live.with_name(live.name + ".restore") if live is not None else plain
        if live is not None:
            shutil.copyfile(plain, target)  # next to the live file: replace() stays on one file system
        db.restore(target, url)
    return {"restored": str(path), "kept": str(kept) if kept else None}
