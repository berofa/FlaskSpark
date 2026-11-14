"""ui-otp documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.otp import PAGE


class OtpDocsView(FlaskSparkMethodView):
    """Render the ui-otp documentation page."""

    url = "/components/otp"
    endpoint = "component_otp"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
