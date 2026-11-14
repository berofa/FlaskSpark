"""ui-emoji-picker documentation view (Bootstrap 6)."""

from __future__ import annotations

from flask import render_template
from flaskspark.views.flaskspark_method_view import FlaskSparkMethodView

from app.pages.emoji_picker import PAGE


class EmojiPickerDocsView(FlaskSparkMethodView):
    """Render the ui-emoji-picker documentation page."""

    url = "/components/emoji-picker"
    endpoint = "component_emoji_picker"

    def get(self):
        return render_template("components/_v6.html", page=PAGE)
