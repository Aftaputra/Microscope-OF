from flask import abort, url_for, jsonify, render_template, Blueprint

from openflexure_microscope.common.labthings_core.utilities import get_docstring

from ...resource import Resource
from ...find import current_labthing

import os


class APISpecResource(Resource):
    """
    OpenAPI v3 documentation
    """

    def get(self):
        """
        OpenAPI v3 documentation
        """
        return jsonify(current_labthing().spec.to_dict())


class SwaggerUIResource(Resource):
    """
    Swagger UI documentation
    """

    def get(self):
        return render_template("swagger-ui.html")


class W3CThingDescriptionResource(Resource):
    """
    W3C-style Thing Description
    """

    def get(self):
        props = {}
        for key, prop in current_labthing().properties.items():
            props[key] = {}
            props[key]["title"] = prop.__name__
            props[key]["description"] = get_docstring(prop)
            props[key]["links"] = [
                {"href": current_labthing().url_for(prop, _external=True)}
            ]

        actions = {}
        for key, prop in current_labthing().actions.items():
            actions[key] = {}
            actions[key]["title"] = prop.__name__
            actions[key]["description"] = get_docstring(prop) or (
                get_docstring(prop.post) if hasattr(prop, "post") else ""
            )
            actions[key]["links"] = [
                {"href": current_labthing().url_for(prop, _external=True)}
            ]

        td = {
            "id": url_for("labthings_docs.w3c_td", _external=True),
            "title": current_labthing().title,
            "description": current_labthing().description,
            "properties": props,
            "actions": actions,
        }

        return jsonify(td)


docs_blueprint = Blueprint(
    "labthings_docs", __name__, static_folder="./static", template_folder="./templates"
)

docs_blueprint.add_url_rule(
    "/swagger", view_func=APISpecResource.as_view("swagger_json")
)
docs_blueprint.add_url_rule(
    "/swagger-ui", view_func=SwaggerUIResource.as_view("swagger_ui")
)
docs_blueprint.add_url_rule(
    "/td", view_func=W3CThingDescriptionResource.as_view("w3c_td")
)
