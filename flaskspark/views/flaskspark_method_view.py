"""
Base method view helpers for FlaskSpark.

Lets every view serve HTML for browsers and JSON for API clients from the same
URL (content negotiation via Accept header, `?format=json` or a JSON body).
"""

from flask import flash, jsonify, redirect, render_template
from flask.views import MethodView

from flaskspark.helpers.content_negotiation import to_jsonable, wants_json


class FlaskSparkMethodView(MethodView):
    """
    Base class for FlaskSpark class-based views.
    """

    @staticmethod
    def wants_json():
        """
        Return True if the current request expects a JSON response.

        Args:
            None

        Returns:
            bool: True for JSON, False for HTML.
        """
        return wants_json()

    def return_response(self, data, template=None, status=200, context=None,
                        redirect_to=None, message=None, category="success"):
        """
        Return the view's data as JSON or as HTML, depending on the request.

        JSON: `data` is converted to JSON-serialisable types and returned with
        `status`. HTML: if `redirect_to` is given (typical after a POST), `message`
        is flashed and the client is redirected; otherwise `template` is rendered
        with `data` and `context` as template variables.

        Args:
            data (dict | list): The payload; also the template variables if it is a dict.
            template (str, optional): Template to render for HTML requests.
            status (int, optional): HTTP status code. Defaults to 200.
            context (dict, optional): Additional template variables (HTML only, not exposed as JSON).
            redirect_to (str, optional): URL to redirect HTML clients to instead of rendering.
            message (str, optional): Flash message for HTML clients (only with `redirect_to`).
            category (str, optional): Flash category. Defaults to "success".

        Returns:
            Response: A Flask response object.

        Raises:
            ValueError: If neither `template` nor `redirect_to` is given for an HTML request.
            jinja2.TemplateNotFound: If the template exists neither in the application nor in FlaskSpark.
        """
        if wants_json():
            return jsonify(to_jsonable(data)), status

        if redirect_to:
            if message:
                flash(message, category)
            return redirect(redirect_to)

        if not template:
            raise ValueError("return_response() needs a template or redirect_to for HTML requests.")

        # The Jinja loader searches the application templates first, then FlaskSpark's.
        variables = dict(data) if isinstance(data, dict) else {"data": data}
        variables.update(context or {})
        return render_template(template, **variables), status

    def return_error(self, message, status=400, redirect_to=None, category="danger", **details):
        """
        Return an error as JSON (`{"error": ..., **details}`) or flash it and redirect.

        Args:
            message (str): Human-readable error message.
            status (int, optional): HTTP status code for JSON clients. Defaults to 400.
            redirect_to (str, optional): URL to redirect HTML clients to. Without it,
                HTML clients get a plain error response with `status`.
            category (str, optional): Flash category. Defaults to "danger".
            **details: Additional fields for the JSON body.

        Returns:
            Response: A Flask response object.
        """
        if wants_json():
            return jsonify(to_jsonable({"error": message, **details})), status

        if redirect_to:
            flash(message, category)
            return redirect(redirect_to)

        return message, status
