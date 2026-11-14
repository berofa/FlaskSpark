"""The start page: the tiles of the modules and the sections they add (PAGE_SECTIONS["home"]). A signed-in visitor
whose role gives no area at all sees «no access» instead.

It is a fallback: a view of a module or of the app on «/» replaces it (FlaskSpark registers it only when no other view
claims «/»). With config.yaml `app.start` (a path or an endpoint) it sends the visitor there."""

from __future__ import annotations

from flask import redirect, render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from flaskspark.core.web import OPEN, get_access, start_url


class HomeView(FlaskSparkMethodView):
    url = "/"
    endpoint = "index"
    area = OPEN
    fallback = True

    def get(self):
        target = start_url()
        if target:
            return redirect(target)
        if not get_access().may_use_any():
            return render_template("flaskspark/no_access.html"), 403
        return render_template("flaskspark/home.html")
