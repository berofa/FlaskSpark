"""Files attached to an item of a module (images, videos and documents with a title and a description).

An attachment belongs to an item of an owner type (owner_type + owner_id, e.g. "note" 12). A module describes its
kind of item with an AttachmentOwner (who may see and change the files of an item) and names it in its manifest:

    ATTACHMENT_OWNERS = ("modules.notes.files:NoteFiles",)

    class NoteFiles(attachments.AttachmentOwner):
        TYPE, AREA = "note", "notes"
        SHAREABLE = "note"            # who may read / write: the item's shares (flaskspark.core.shares)

        # or its own checks:
        def can_read(self, s, user_id, owner_id): ...
        def can_write(self, s, user_id, owner_id): ...

The page shows them with <ui-attachments owner-type="note" owner-id="12"> (upload by dropping, a gallery with a
lightbox, documents as a list); when the module deletes an item, its files go along:

    attachments.delete_for("note", note.id, session=s)   # rows now, files after the commit

- Storage: below the directory of the owner type's store (AttachmentOwner.STORE, default the module's name):
  config.yaml attachments.stores.<store>, else <attachments.dir>/<store>, else STATE_DIR/attachments/<store> (part of
  the backups). An owner type with a folder() keeps them in order there (<folder…>/<kind>-<NN><ext>); without one
  <yyyy>/<mm>/<uuid><ext>. Never the user's file name. attachments.require_marker: a configured directory must carry
  the marker file MARKER (e.g. a network mount that is not there: nothing is written or read).
- Uploads are written to the disk while they arrive (no whole file in memory), with size and SHA-256, at most
  attachments.max_size_mb (default 100, 0: no limit).
- Thumbnails (WebP, THUMB_PX) in attachments.thumbs_dir (default STATE_DIR/attachments/.thumbs, left out of the
  backups: they are made again from the originals): images with Pillow (HEIC with pillow-heif), PDFs their first
  page (pypdfium2), videos a frame (ffmpeg on the PATH). All optional (the extra flaskspark[files]): without them
  there are no thumbnails, everything else works and the page shows the file type.
- Images browsers can't show (HEIC, TIFF) get a JPEG for the lightbox, made once and kept next to the thumbnails.
- Deleting rows removes their files after the commit.

The table core_attachments is the core's; every function takes an optional session (`session=`) of the owner's
module, else it opens one: the owner's methods run with the module's rights, the core's table with the core's.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import time
import uuid
from abc import ABC
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from . import db, paths
from .module import N_

log = logging.getLogger(__name__)

IMAGE, VIDEO, DOCUMENT = "image", "video", "document"
MARKER = ".flaskspark-attachments"
THUMBS = ".thumbs"  # below STATE_DIR/attachments (default)
THUMB_PX = 480
DISPLAY_PX = 2560
CHUNK = 1024 * 1024
DEFAULT_MAX_MB = 100
VIDEO_FRAME_AT = 3.0  # seconds into a video for its thumbnail (the first frame is often black)
#: images the browsers don't show: a JPEG for the lightbox
CONVERT_FOR_DISPLAY = {"image/heic", "image/heif", "image/tiff"}


class AttachmentError(ValueError):
    """A request that is not possible. template and params: the English source text; status: the HTTP answer."""

    status = 400

    def __init__(self, template: str, **params):
        self.template, self.params = template, params
        super().__init__(template % params if params else template)


class NotFound(AttachmentError):
    """Unknown, or not the visitor's to see (both alike)."""

    status = 404


class TooLarge(AttachmentError):
    status = 413


class StorageUnavailable(AttachmentError):
    status = 503


class AttachmentOwner(ABC):
    """A kind of item that may have attachments. TYPE: its key (unique in the application, e.g. "note"), AREA: the
    area a visitor needs ("": none beyond the item's own checks), STORE: its storage (default the module's name),
    SHAREABLE: a share type (flaskspark.core.shares) whose rights decide (read: see the files, write: change them).
    MODULE is set by the core: the module whose manifest names it.

    Without SHAREABLE an owner overrides can_read (and can_write, default like reading); else nobody may."""

    TYPE: str = ""
    AREA: str = ""
    STORE: str = ""
    SHAREABLE: str = ""
    MODULE: str = ""

    def can_read(self, s, user_id: int, owner_id: int) -> bool:
        """May the user see the files of the item (unknown items: no)?"""
        if self.SHAREABLE:
            from . import shares

            return shares.can_read(user_id, self.SHAREABLE, owner_id, session=s)
        return False

    def can_write(self, s, user_id: int, owner_id: int) -> bool:
        """May the user add, change and delete them?"""
        if self.SHAREABLE:
            from . import shares

            return shares.can_write(user_id, self.SHAREABLE, owner_id, session=s)
        return self.can_read(s, user_id, owner_id)

    def folder(self, s, owner_id: int) -> list[str] | None:
        """Where the item's files go below the store (names unique per item, safe_name() makes them safe), e.g.
        [category, item]; None: by date."""
        return None

    def audience(self, s, owner_id: int) -> set[int]:
        """Users whose pages show the item: told after a change (event "attachments")."""
        if self.SHAREABLE:
            from . import shares

            return shares.audience(self.SHAREABLE, owner_id, session=s)
        return set()

    @property
    def store(self) -> str:
        return self.STORE or self.MODULE or db.CORE


# --- the registry -------------------------------------------------------------------------------------------------
_registered: dict[str, AttachmentOwner] = {}
_cache: dict[tuple, dict[str, AttachmentOwner]] = {}


def register(owner: AttachmentOwner, module: str = db.CORE) -> AttachmentOwner:
    """Make an owner type usable without a manifest entry; `module`: whose rights its methods run with."""
    if not owner.TYPE:
        raise TypeError(f"{type(owner).__name__}: TYPE is required")
    owner.MODULE = owner.MODULE or module
    _registered[owner.TYPE] = owner
    _cache.clear()
    return owner


def registry(cfg=None) -> dict[str, AttachmentOwner]:
    """Every owner type: the manifests' ATTACHMENT_OWNERS (of the loaded modules) and register()'s."""
    from . import config, modules

    cfg = cfg if cfg is not None else config.load()
    manifests = modules.load(cfg)
    key = tuple(m.NAME for m in manifests)
    if key not in _cache:
        found: dict[str, AttachmentOwner] = {}
        for manifest in manifests:
            for spec in manifest.ATTACHMENT_OWNERS or ():
                owner = modules.resolve(spec)()
                if not owner.TYPE:
                    raise TypeError(f"{spec}: TYPE is required")
                if owner.TYPE in found:
                    raise TypeError(f"{spec}: the owner type {owner.TYPE!r} exists already "
                                    f"(module {found[owner.TYPE].MODULE!r})")
                owner.MODULE = manifest.NAME
                found[owner.TYPE] = owner
        _cache[key] = {**found, **_registered}
    return _cache[key]


def owner(owner_type: str) -> AttachmentOwner:
    found = registry().get(owner_type)
    if found is None:
        raise NotFound(N_("Not found."))
    return found


@contextmanager
def _session(kind: AttachmentOwner, session=None):
    if session is not None:
        yield session
    else:
        with db.for_module(kind.MODULE or db.CORE).session() as s:
            yield s


def reset() -> None:
    """Forget the registry (tests)."""
    _registered.clear()
    _cache.clear()


# --- storage ----------------------------------------------------------------------------------------------------
def settings(cfg=None) -> dict:
    from . import config

    cfg = cfg if cfg is not None else config.load()
    return (cfg.section("attachments") if cfg is not None else None) or {}


def max_size(cfg=None) -> int:
    """The largest upload in bytes (0: no limit)."""
    try:
        mb = float(settings(cfg).get("max_size_mb", DEFAULT_MAX_MB))
    except (TypeError, ValueError):
        mb = DEFAULT_MAX_MB
    return int(mb * 1024 * 1024) if mb > 0 else 0


@dataclass(frozen=True)
class Storage:
    root: Path  # originals
    thumbs: Path  # thumbnails and display versions (regenerable)
    marker: bool = False  # the root must carry MARKER

    def ready(self) -> bool:
        if self.marker:
            return (self.root / MARKER).is_file()
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
        return self.root.is_dir()

    def require(self) -> Path:
        if not self.ready():
            raise StorageUnavailable(N_("The file storage is not available. Please try again later."))
        return self.root

    def original(self, att) -> Path:
        path = (self.require() / att.path).resolve()
        if self.root.resolve() not in path.parents:
            raise NotFound(N_("File not found."))
        return path

    def thumb(self, att) -> Path:
        return self.thumbs / f"{att.id}.webp"

    def display(self, att) -> Path:
        return self.thumbs / f"{att.id}-display.jpg"


def thumbs_dir(cfg=None) -> Path:
    """Where thumbnails live (marked NOBACKUP: they are made again from the originals)."""
    from .backup import NOBACKUP

    configured = settings(cfg).get("thumbs_dir")
    path = Path(configured).expanduser() if configured else paths.STATE_DIR / "attachments" / THUMBS
    try:
        path.mkdir(parents=True, exist_ok=True)
        (path / NOBACKUP).touch(exist_ok=True)
    except OSError:
        pass
    return path


def storage(store: str, cfg=None) -> Storage:
    """The storage `store`: attachments.stores.<store>, else <attachments.dir>/<store>, else
    STATE_DIR/attachments/<store>."""
    section = settings(cfg)
    explicit = (section.get("stores") or {}).get(store)
    if explicit:
        root = Path(explicit).expanduser()
    elif section.get("dir"):
        root = Path(section["dir"]).expanduser() / store
    else:
        root = paths.STATE_DIR / "attachments" / store
    marker = bool(section.get("require_marker")) and bool(explicit or section.get("dir"))
    return Storage(root, thumbs_dir(cfg), marker)


def storage_for(owner_type: str, cfg=None) -> Storage:
    return storage(owner(owner_type).store, cfg)


def safe_name(text: str, fallback: str = "Untitled") -> str:
    """A folder name from a user's name: only letters, digits, "-", "_" and single spaces, the first letter upper
    case."""
    name = re.sub(r"[^\w \-]", "", str(text or ""))
    name = re.sub(r"\s+", " ", name).strip()[:100].strip()
    return (name[0].upper() + name[1:]) if name else fallback


def unique_names(rows: Iterable[tuple[object, str]]) -> dict[object, str]:
    """key -> safe_name, unique within `rows` (key, name; keys sortable): the lowest key keeps the name, the others
    get " 2", " 3" …"""
    out: dict = {}
    taken: dict[str, int] = {}
    for row_id, name in sorted(rows):
        base = safe_name(name)
        n = taken.get(base.lower(), 0) + 1
        taken[base.lower()] = n
        out[row_id] = base if n == 1 else f"{base} {n}"
    return out


def _ext(name: str, mime: str) -> str:
    ext = Path(name).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", ext):
        ext = (mimetypes.guess_extension(mime) or ".bin").lower()
    return ".jpg" if ext in (".jpeg", ".jpe") else ext


def _free_name(folder: Path, kind: str, ext: str, taken: set[str]) -> str:
    """The next free "<kind>-NN<ext>" in `folder` (NN counts per kind, also over other extensions)."""
    pattern = re.compile(rf"{kind}-(\d+)\.")
    used = {int(m.group(1)) for name in taken | {p.name for p in folder.glob(f"{kind}-*")} if (m := pattern.match(name))}
    return f"{kind}-{max(used, default=0) + 1:02d}{ext}"


def _prune(root: Path, folder: Path) -> None:
    """Remove `folder` and its parents below `root` while they are empty."""
    root, folder = root.resolve(), folder.resolve()
    while folder != root and root in folder.parents:
        try:
            folder.rmdir()
        except OSError:
            return
        folder = folder.parent


def kind_of(mime: str) -> str:
    if mime.startswith("image/"):
        return IMAGE
    if mime.startswith("video/"):
        return VIDEO
    return DOCUMENT


def _mime(name: str, given: str | None) -> str:
    given = (given or "").split(";")[0].strip().lower()
    if given and given != "application/octet-stream":
        return given[:100]
    guessed = mimetypes.guess_type(name)[0]
    if guessed is None and name.lower().endswith((".heic", ".heif")):
        guessed = "image/heic"
    return guessed or "application/octet-stream"


def _text(value, label: str, limit: int | None, required: bool = False) -> str | None:
    text = str(value or "").strip()
    if required and not text:
        raise AttachmentError(N_("%(label)s is missing."), label=label)
    if limit and len(text) > limit:
        raise AttachmentError(N_("%(label)s is too long (at most %(n)s characters)."), label=label, n=limit)
    return text or None


def default_title(name: str) -> str:
    stem = Path(name).stem.strip() or name.strip() or "File"
    return stem[:200]


# --- rights -------------------------------------------------------------------------------------------------------
def _check(s, kind: AttachmentOwner, user_id: int | None, owner_id: int, write: bool) -> None:
    if user_id is None:
        return  # the module itself
    if not (kind.can_write if write else kind.can_read)(s, user_id, owner_id):
        raise NotFound(N_("Not found."))


def check(user_id: int, owner_type: str, owner_id: int, write: bool = False, session=None) -> None:
    """NotFound unless `user_id` may read (write: change) the files of the item (unknown ones alike)."""
    kind = owner(owner_type)
    with _session(kind, session) as s:
        _check(s, kind, user_id, owner_id, write)


def _row(s, attachment_id: int):
    from .models import Attachment

    with db.as_core(s):
        return s.get(Attachment, attachment_id)


def attachment_of(user_id: int | None, attachment_id: int, write: bool = False, session=None):
    """The attachment if the user may see it (write: change it), else NotFound. user_id None: the module itself.
    session: the module's (its work not committed yet is seen), else one of the owner's module."""
    if session is not None:
        att = _row(session, attachment_id)
    else:
        with db.session() as s:
            att = s.get(_model(), attachment_id)
    owner_type = att.owner_type if att is not None else None
    if owner_type is None or owner_type not in registry():
        raise NotFound(N_("File not found."))
    kind = owner(owner_type)
    with _session(kind, session) as s:
        att = _row(s, attachment_id)
        try:
            _check(s, kind, user_id, att.owner_id, write)
        except NotFound:
            raise NotFound(N_("File not found.")) from None
        return att


def _model():
    from .models import Attachment

    return Attachment


# --- reading ------------------------------------------------------------------------------------------------------
def _of_owner(s, owner_type: str, owner_id: int) -> list:
    Attachment = _model()
    with db.as_core(s):
        return list(s.scalars(db.select(Attachment).where(Attachment.owner_type == owner_type,
                                                          Attachment.owner_id == owner_id)
                              .order_by(Attachment.sorting, Attachment.id)))


def of_owner(owner_type: str, owner_id: int, session=None) -> list:
    """The item's attachments in their order (no rights checked: the module's own use)."""
    with _session(owner(owner_type), session) as s:
        return _of_owner(s, owner_type, owner_id)


def counts(owner_type: str, owner_ids: Iterable[int], session=None) -> dict[int, int]:
    """owner_id -> number of attachments (for a list)."""
    Attachment = _model()
    ids = list(owner_ids)
    if not ids:
        return {}
    with _session(owner(owner_type), session) as s, db.as_core(s):
        rows = s.execute(db.select(Attachment.owner_id, db.func.count()).where(
            Attachment.owner_type == owner_type, Attachment.owner_id.in_(ids)).group_by(Attachment.owner_id))
        return {owner_id: n for owner_id, n in rows}


def _url(att_id: int, sha256: str, what: str) -> str:
    """URL of a file's thumbnail or original; ?v= changes with the content, so a browser never shows a cached file
    for another one (SQLite reuses the ids of deleted rows)."""
    return f"/attachments/{att_id}/{what}?v={sha256[:12]}"


def first_images(owner_type: str, owner_ids: Iterable[int], session=None) -> dict[int, str]:
    """owner_id -> thumbnail URL of its first image (or video) for a list."""
    Attachment = _model()
    ids = list(owner_ids)
    if not ids:
        return {}
    out: dict[int, str] = {}
    with _session(owner(owner_type), session) as s, db.as_core(s):
        rows = s.execute(db.select(Attachment.owner_id, Attachment.id, Attachment.sha256).where(
            Attachment.owner_type == owner_type, Attachment.owner_id.in_(ids), Attachment.kind.in_((IMAGE, VIDEO)))
            .order_by(Attachment.kind, Attachment.sorting, Attachment.id)).all()  # images ("image" < "video") first
    for owner_id, att_id, sha256 in rows:
        out.setdefault(owner_id, _url(att_id, sha256, "thumb"))
    return out


def serialize(att, st: Storage | None = None) -> dict:
    st = st or storage_for(att.owner_type)
    return {
        "id": att.id, "kind": att.kind, "title": att.title, "description": att.description or "",
        "name": att.original_name, "mime": att.mime, "size": att.size, "uploaded": att.uploaded,
        "thumb": _url(att.id, att.sha256, "thumb") if st.thumb(att).is_file() else None,
        "url": _url(att.id, att.sha256, "file"),
    }


# --- writing ------------------------------------------------------------------------------------------------------
def store(user_id: int | None, owner_type: str, owner_id: int, stream: BinaryIO, name: str, mime: str | None = None,
          title: str | None = None, description: str | None = None, cfg=None, session=None):
    """Write the upload from `stream` to the storage (chunk by chunk, at most max_size()) and record it; the
    thumbnail follows (best effort). user_id: the uploading user (their right to change the item is checked); None:
    the module itself."""
    Attachment = _model()
    kind = owner(owner_type)
    st = storage(kind.store, cfg)
    limit = max_size(cfg)
    with _session(kind, session) as s:
        _check(s, kind, user_id, owner_id, write=True)
        root = st.require()
        name = Path(str(name or "").replace("\\", "/")).name.strip()[:255] or "file"
        mime = _mime(name, mime)
        title = _text(title, N_("Title"), 200) or default_title(name)
        file_kind = kind_of(mime)
        ext = _ext(name, mime)
        names = kind.folder(s, owner_id)
        folder = root / (Path(*names) if names is not None else Path(time.strftime("%Y")) / time.strftime("%m"))
        folder.mkdir(parents=True, exist_ok=True)
        part = folder / f".{uuid.uuid4().hex}.part"
        digest, size = hashlib.sha256(), 0
        try:
            with open(part, "wb") as out:
                while chunk := stream.read(CHUNK):
                    size += len(chunk)
                    if limit and size > limit:
                        raise TooLarge(N_("The file is too large (at most %(size)s)."), size=human_size(limit))
                    out.write(chunk)
                    digest.update(chunk)
                out.flush()
                os.fsync(out.fileno())
            if size == 0:
                raise AttachmentError(N_("The file is empty."))
            taken = {Path(a.path).name for a in _of_owner(s, owner_type, owner_id)}
            target = folder / (_free_name(folder, file_kind, ext, taken) if names is not None
                               else f"{uuid.uuid4().hex}{ext}")
            part.rename(target)
        except BaseException:
            part.unlink(missing_ok=True)
            _prune(root, folder)
            raise
        def discard():
            target.unlink(missing_ok=True)
            _prune(root, folder)

        try:
            with db.as_core(s):
                last = s.scalar(db.select(Attachment.sorting).where(Attachment.owner_type == owner_type,
                                                                    Attachment.owner_id == owner_id)
                                .order_by(Attachment.sorting.desc()).limit(1))
                att = Attachment(module=kind.MODULE or db.CORE, owner_type=owner_type, owner_id=owner_id,
                                 kind=file_kind, title=title, description=_text(description, N_("Description"), None),
                                 original_name=name, mime=mime, size=size, sha256=digest.hexdigest(),
                                 path=target.relative_to(root).as_posix(), sorting=(last or 0) + 1,
                                 uploaded_by=user_id, uploaded=time.time())
                s.add(att)
                s.flush()
        except BaseException:
            discard()
            raise
        db.after_rollback(s, discard)  # the row never comes (the caller's session rolls back): the file goes
    ensure_thumb(st, att)
    return att


def update(user_id: int | None, attachment_id: int, changes: dict, session=None, cfg=None):
    """Title (required) and description. cfg: like store()'s (nothing of it is needed today)."""
    att = attachment_of(user_id, attachment_id, write=True, session=session)
    with _session(owner(att.owner_type), session) as s, db.as_core(s):
        att = s.get(_model(), attachment_id)
        if "title" in changes:
            att.title = _text(changes["title"], N_("Title"), 200, required=True)
        if "description" in changes:
            att.description = _text(changes["description"], N_("Description"), None)
        s.flush()
        return att


def reorder(user_id: int | None, owner_type: str, owner_id: int, ids: list[int], session=None) -> list:
    """The order of the item's files: `ids` first in this order, the others after them as they were."""
    kind = owner(owner_type)
    with _session(kind, session) as s:
        _check(s, kind, user_id, owner_id, write=True)
        rows = _of_owner(s, owner_type, owner_id)
        position = {i: n for n, i in enumerate(ids)}
        rows.sort(key=lambda a: (position.get(a.id, len(ids)), a.sorting, a.id))
        with db.as_core(s):
            for n, att in enumerate(rows, 1):
                att.sorting = n
            s.flush()
        return rows


def _remove_later(s, files: list[tuple[int, str, str]], cfg=None) -> None:
    """Remove the files of deleted rows once the session committed: (id, store, path), from the storage of `cfg`."""
    if files:
        db.after_commit(s, lambda: remove_files(files, cfg))


def delete(user_id: int | None, attachment_id: int, session=None, cfg=None) -> None:
    """Delete one attachment (its files after the commit, from the storage of `cfg`)."""
    att = attachment_of(user_id, attachment_id, write=True, session=session)
    kind = owner(att.owner_type)
    with _session(kind, session) as s, db.as_core(s):
        row = s.get(_model(), attachment_id)
        files = [(row.id, kind.store, row.path)]
        s.delete(row)
        s.flush()
        _remove_later(s, files, cfg)


def delete_for(owner_type: str, owner_ids, session=None, cfg=None) -> int:
    """The item (or items) is being deleted: its attachments go, rows now, files after the commit (the module
    checked the right; from the storage of `cfg`). Returns how many."""
    Attachment = _model()
    ids = [owner_ids] if isinstance(owner_ids, int) else list(owner_ids)
    if not ids:
        return 0
    kind = owner(owner_type)
    with _session(kind, session) as s, db.as_core(s):
        rows = s.scalars(db.select(Attachment).where(Attachment.owner_type == owner_type,
                                                     Attachment.owner_id.in_(ids))).all()
        files = [(a.id, kind.store, a.path) for a in rows]
        s.execute(db.delete(Attachment).where(Attachment.owner_type == owner_type, Attachment.owner_id.in_(ids)))
        _remove_later(s, files, cfg)
        return len(files)


def remove_files(files: Iterable[tuple[int, str, str]], cfg=None) -> None:
    """Remove originals, thumbnails and display versions of deleted rows. Without the storage the originals stay
    (logged): an orphan is better than a row without its file."""
    thumbs = thumbs_dir(cfg)
    for att_id, store_name, rel in files:
        for local in (thumbs / f"{att_id}.webp", thumbs / f"{att_id}-display.jpg"):
            local.unlink(missing_ok=True)
        st = storage(store_name, cfg)
        if not st.ready():
            log.warning("attachments: storage %s not ready, %s stays", store_name, rel)
            continue
        path = (st.root / rel).resolve()
        if st.root.resolve() in path.parents:
            path.unlink(missing_ok=True)
            _prune(st.root, path.parent)


def human_size(size: int) -> str:
    value, unit = float(size), 0
    units = ["B", "kB", "MB", "GB", "TB"]
    while value >= 1000 and unit < len(units) - 1:
        value /= 1000
        unit += 1
    return f"{value:.0f} {units[unit]}" if unit == 0 else f"{value:.1f} {units[unit]}"


# --- thumbnails ---------------------------------------------------------------------------------------------------
def thumbnails_available() -> dict[str, bool]:
    """Which thumbnails can be made here: image (Pillow), heic (pillow-heif), pdf (pypdfium2), video (ffmpeg)."""
    import importlib.util

    has = lambda name: importlib.util.find_spec(name) is not None  # noqa: E731
    return {"image": has("PIL"), "heic": has("PIL") and has("pillow_heif"), "pdf": has("PIL") and has("pypdfium2"),
            "video": has("PIL") and shutil.which("ffmpeg") is not None}


def _open_image(path: Path):
    from PIL import Image, ImageOps

    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except ImportError:  # HEIC then has no thumbnail
        pass
    return ImageOps.exif_transpose(Image.open(path))


def _save_webp(image, target: Path, px: int) -> None:
    image = image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")
    image.thumbnail((px, px))
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    image.save(tmp, "WEBP", quality=80)
    tmp.replace(target)


def _video_frame(path: Path, target: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg missing")
    frame = target.with_suffix(".png")
    frame.parent.mkdir(parents=True, exist_ok=True)
    for at in (VIDEO_FRAME_AT, 0.0):  # a video shorter than VIDEO_FRAME_AT: its first frame
        subprocess.run([ffmpeg, "-v", "error", "-y", "-ss", str(at), "-i", str(path), "-frames:v", "1", str(frame)],
                       check=False, timeout=120, capture_output=True)
        if frame.is_file() and frame.stat().st_size:
            break
    try:
        from PIL import Image

        _save_webp(Image.open(frame), target, THUMB_PX)
    finally:
        frame.unlink(missing_ok=True)


def _pdf_page(path: Path, target: Path) -> None:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(path))
    try:
        page = pdf[0]
        _save_webp(page.render(scale=THUMB_PX / max(page.get_size())).to_pil(), target, THUMB_PX)
    finally:
        pdf.close()


def ensure_thumb(st: Storage, att, force: bool = False) -> bool:
    """Make the thumbnail if it is missing (force: anew); False if the file has none (no library for it, the storage
    away, an unreadable file)."""
    target = st.thumb(att)
    if target.is_file() and not force:
        return True
    if not st.ready():
        return False
    try:
        path = st.original(att)
        if att.kind == IMAGE:
            _save_webp(_open_image(path), target, THUMB_PX)
        elif att.kind == VIDEO:
            _video_frame(path, target)
        elif att.mime == "application/pdf":
            _pdf_page(path, target)
        else:
            return False
    except Exception as exc:  # noqa: BLE001 - no thumbnail is no error, the page shows the file type
        log.info("attachments: no thumbnail for %s (%s): %s", att.id, att.mime, exc)
        return False
    return target.is_file()


def display_file(st: Storage, att) -> tuple[Path, str]:
    """The file the lightbox shows: the original, or a JPEG of it for images browsers can't show (made once; the
    original when that is not possible)."""
    if att.kind != IMAGE or att.mime not in CONVERT_FOR_DISPLAY:
        return st.original(att), att.mime
    target = st.display(att)
    if not target.is_file():
        try:
            image = _open_image(st.original(att)).convert("RGB")
        except Exception as exc:  # noqa: BLE001 - no converter: the original
            log.info("attachments: %s not converted for display: %s", att.id, exc)
            return st.original(att), att.mime
        image.thumbnail((DISPLAY_PX, DISPLAY_PX))
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        image.save(tmp, "JPEG", quality=88)
        tmp.replace(target)
    return target, "image/jpeg"


def make_thumbs(cfg=None, force: bool = False) -> tuple[int, int]:
    """Make the missing thumbnails of all files (force: all anew): (made, without one)."""
    Attachment = _model()
    known = registry(cfg)
    made = missing = 0
    with db.session() as s:
        rows = list(s.scalars(db.select(Attachment).order_by(Attachment.id)))
    for att in rows:
        if att.owner_type not in known:
            continue
        st = storage(known[att.owner_type].store, cfg)
        had = st.thumb(att).is_file()
        if ensure_thumb(st, att, force=force):
            made += (not had) or force
        else:
            missing += 1
    return made, missing


def tidy(owner_type: str, cfg=None) -> int:
    """Move the files of `owner_type` to where its folder() puts them now (after a rename or a move) and remove the
    folders left empty; returns how many moved. Each move is committed at once (the file goes back if its row can't
    be saved), so there is no session to hand over. Without the storage (of `cfg`) nothing moves."""
    Attachment = _model()
    kind = owner(owner_type)
    st = storage(kind.store, cfg)
    if not st.ready():
        return 0
    moved = 0
    with db.for_module(kind.MODULE or db.CORE).session() as s:
        with db.as_core(s):
            ids = [a.id for a in s.scalars(db.select(Attachment).where(Attachment.owner_type == owner_type)
                                           .order_by(Attachment.owner_id, Attachment.sorting, Attachment.id))]
    for att_id in ids:
        with db.for_module(kind.MODULE or db.CORE).session() as s:
            att = _row(s, att_id)
            names = kind.folder(s, att.owner_id)
            if names is None:
                continue  # kept by date: nothing to tidy
            folder, current = Path(*names), Path(att.path)
            if current.parent == folder:
                continue
            source, target_dir = st.root / current, st.root / folder
            if not source.is_file():
                log.warning("attachments: %s missing, not moved", current)
                continue
            target_dir.mkdir(parents=True, exist_ok=True)
            name = current.name
            if (target_dir / name).exists():
                name = _free_name(target_dir, att.kind, current.suffix, set())
            target = target_dir / name
            source.rename(target)
            try:
                with db.as_core(s):
                    att.path = (folder / name).as_posix()
                    s.flush()
            except Exception:
                target.rename(source)
                raise
        moved += 1
        _prune(st.root, source.parent)
    return moved
