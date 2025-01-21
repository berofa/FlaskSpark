"""
Main view module for the Flask application.

This module defines the `MainView` class, which represents the main entry point 
for authenticated users. It enforces login requirements and handles rendering the 
main page of the application.

Classes:
    MainView: A class-based view for the main page, accessible only to authenticated users.
"""

from flask import jsonify, request
from flask import current_app, render_template as flask_render_template
from flask.views import MethodView
import os

class FlaskSparkMethodView(MethodView):
    """
    Class-based view for the main page of the application.

    This view requires the user to be authenticated before accessing it. The main 
    page is rendered using an HTML template.
    """

    # Restrict access to authenticated users only
    #decorators = [login_required]
    
    #@staticmethod
    def return_response(self, data, template=None):
        """
        Generates a response based on the request type.

        This function determines whether the request expects a JSON or HTML response. 
        If the request expects JSON, it returns a JSON response with the given data. 
        If an HTML template is provided, it renders the template using the data.

        Args:
            data (dict): The data to include in the response, either as JSON or for rendering the template.
            template (str, optional): The name of the HTML template to render. Defaults to None.

        Returns:
            Response: A Flask response object containing either JSON data or rendered HTML content.
        """
        if request.is_json:
            # Return JSON response if the request expects JSON
            return jsonify(data)
        
        # Applikations-Templates prüfen
        template_path_app = os.path.join(current_app.template_folder, template)
        if os.path.exists(template_path_app):
            return flask_render_template(template, **data)
        
        # FlaskSpark-Templates prüfen
        flaskspark_template_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../templates")
        )
        template_path_spark = os.path.join(flaskspark_template_dir, template)

        if os.path.exists(template_path_spark):
            # FlaskSpark-Templates verwenden
            return flask_render_template(template, **data)
        
        # Fehler ausgeben, wenn das Template nicht gefunden wurde
        raise FileNotFoundError(f"Template '{template}' not found in application or FlaskSpark.")

        # Render and return HTML response if the request does not expect JSON
        #return render_template(template, **data)
