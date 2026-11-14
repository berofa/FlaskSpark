"""Files attached to items of the modules (flaskspark.core.attachments), for <ui-attachments>. Every request is
checked against the owner type: its area (AttachmentOwner.AREA) and its own check whether the visitor may read or
change that item. Unknown items and files and those of others alike answer 404.

GET  /api/attachments/<type>/<id>          {attachments: [{id, kind, title, description, name, mime, size, thumb,
                                           url}], ready: the storage is available, max_size: bytes (0: no limit)}
POST /api/attachments/<type>/<id>          upload: the file as the raw body (streamed to the storage), headers
                                           X-File-Name (URI-encoded) and Content-Type; optional X-Title ->
                                           {attachment, message}; 413 when too large
POST /api/attachments/<type>/<id>/order    {ids: [...]} -> {attachments}
POST /api/attachments/<att>                {action: update (title, description) | delete} -> {attachment} / {ok}
GET  /attachments/<att>/thumb              the thumbnail (WebP), made from the original when missing; 404 without one
GET  /attachments/<att>/file               the original (Range for videos); ?display=1: what the lightbox shows (HEIC
                                           and TIFF as JPEG), ?download=1: as a download under its file name

After a change the users who see the item (AttachmentOwner.audience) get the event "attachments" (owner_type,
owner_id).
"""

from __future__ import annotations

from urllib.parse import unquote

from flask import abort, jsonify, request, send_file
from flask_babel import gettext
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core import attachments, config, db, events
from flaskspark.core.web import OPEN, can, user_id

CACHE_SECONDS = 86400


def _ok(data: dict):
    return jsonify(data)


def _fail(error, status: int | None = None):
    if isinstance(error, attachments.AttachmentError):
        params = {k: gettext(v) if k == "label" else v for k, v in error.params.items()}
        return jsonify({"error": gettext(error.template, **params)}), status or error.status
    return jsonify({"error": str(error)}), status or 400


def _owner(owner_type: str):
    """The owner type; 404 when unknown, 403 without its area."""
    try:
        kind = attachments.owner(owner_type)
    except attachments.AttachmentError:
        abort(404)
    if kind.AREA and not can(kind.AREA):
        abort(403)
    return kind


def _tell(kind, owner_id: int) -> None:
    with db.for_module(kind.MODULE or db.CORE).session() as s:
        users = kind.audience(s, owner_id)
    events.emit_users("attachments", users | {user_id()}, owner_type=kind.TYPE, owner_id=owner_id)


def _attachment(attachment_id: int, write: bool = False):
    """The visitor's attachment (its owner's area and checks), else 404."""
    with db.session() as s:
        row = s.get(attachments._model(), attachment_id)
        owner_type = row.owner_type if row is not None else None
    if owner_type is None:
        abort(404)
    _owner(owner_type)
    try:
        return attachments.attachment_of(user_id(), attachment_id, write)
    except attachments.AttachmentError:
        abort(404)


class AttachmentsOwnerApiView(FlaskSparkMethodView):
    url = "/api/attachments/<owner_type>/<int:owner_id>"
    endpoint = "core_attachments"
    area = OPEN

    def get(self, owner_type: str, owner_id: int):
        kind = _owner(owner_type)
        cfg = config.load()
        st = attachments.storage(kind.store, cfg)
        try:
            attachments.check(user_id(), owner_type, owner_id)
            rows = attachments.of_owner(owner_type, owner_id)
        except attachments.AttachmentError as error:
            return _fail(error)
        return _ok({"attachments": [attachments.serialize(a, st) for a in rows], "ready": st.ready(),
                    "max_size": attachments.max_size(cfg)})

    def post(self, owner_type: str, owner_id: int):
        kind = _owner(owner_type)
        cfg = config.load()
        limit = attachments.max_size(cfg)
        if limit and request.content_length and request.content_length > limit:
            return _fail(attachments.TooLarge("The file is too large (at most %(size)s).",
                                              size=attachments.human_size(limit)))
        name = unquote(request.headers.get("X-File-Name") or "")
        title = unquote(request.headers.get("X-Title") or "") or None
        try:
            att = attachments.store(user_id(), owner_type, owner_id, request.stream, name,
                                    request.headers.get("Content-Type"), title, cfg=cfg)
        except attachments.AttachmentError as error:
            return _fail(error)
        _tell(kind, owner_id)
        return _ok({"attachment": attachments.serialize(att), "message": gettext("«%(title)s» uploaded.",
                                                                                  title=att.title)})


class AttachmentsOrderApiView(FlaskSparkMethodView):
    url = "/api/attachments/<owner_type>/<int:owner_id>/order"
    endpoint = "core_attachments_order"
    area = OPEN

    def post(self, owner_type: str, owner_id: int):
        kind = _owner(owner_type)
        try:
            ids = [int(i) for i in (request.get_json(silent=True) or {}).get("ids") or []]
        except (TypeError, ValueError):
            return _fail(gettext("The order is not readable."))
        try:
            rows = attachments.reorder(user_id(), owner_type, owner_id, ids)
        except attachments.AttachmentError as error:
            return _fail(error)
        _tell(kind, owner_id)
        return _ok({"attachments": [attachments.serialize(a) for a in rows]})


class AttachmentApiView(FlaskSparkMethodView):
    url = "/api/attachments/<int:attachment_id>"
    endpoint = "core_attachment"
    area = OPEN

    def post(self, attachment_id: int):
        att = _attachment(attachment_id, write=True)
        kind = attachments.owner(att.owner_type)
        body = request.get_json(silent=True) or {}
        action = body.get("action")
        try:
            if action == "update":
                att = attachments.update(user_id(), attachment_id,
                                         {k: body[k] for k in ("title", "description") if k in body})
                out = {"attachment": attachments.serialize(att), "message": gettext("Saved")}
            elif action == "delete":
                attachments.delete(user_id(), attachment_id)
                out = {"ok": True, "message": gettext("File deleted.")}
            else:
                return _fail(gettext("Unknown action."))
        except attachments.AttachmentError as error:
            return _fail(error)
        _tell(kind, att.owner_id)
        return _ok(out)


def _private(response):
    response.cache_control.private = True
    response.cache_control.max_age = CACHE_SECONDS
    return response


class AttachmentThumbView(FlaskSparkMethodView):
    url = "/attachments/<int:attachment_id>/thumb"
    endpoint = "core_attachment_thumb"
    area = OPEN

    def get(self, attachment_id: int):
        att = _attachment(attachment_id)
        st = attachments.storage_for(att.owner_type)
        if not attachments.ensure_thumb(st, att):
            abort(404)
        return _private(send_file(st.thumb(att), mimetype="image/webp", conditional=True))


class AttachmentFileView(FlaskSparkMethodView):
    url = "/attachments/<int:attachment_id>/file"
    endpoint = "core_attachment_file"
    area = OPEN

    def get(self, attachment_id: int):
        att = _attachment(attachment_id)
        st = attachments.storage_for(att.owner_type)
        mime = att.mime
        try:
            if request.args.get("display"):
                path, mime = attachments.display_file(st, att)
            else:
                path = st.original(att)
        except attachments.AttachmentError as error:
            return _fail(error)
        if not path.is_file():
            abort(404)
        # never shown inline as a page of this site: a document a user uploaded could carry scripts (HTML, SVG)
        inline_safe = (mime.startswith(("image/", "video/", "audio/")) and mime != "image/svg+xml") or \
            mime in ("application/pdf", "text/plain")
        response = send_file(path, mimetype=mime if inline_safe else "application/octet-stream", conditional=True,
                             download_name=att.original_name,
                             as_attachment=bool(request.args.get("download")) or not inline_safe)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return _private(response)
