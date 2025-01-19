"""
Base view for FlaskSpark.
"""

from flask.views import MethodView
from flask import render_template

class BaseView(MethodView):
    """
    Base view for the home page.

    Methods:
        get: Handles GET requests.
    """
    def get(self):
        """
        Renders the base template.

        Returns:
            str: Rendered HTML response.
        """
        return render_template("base.html")