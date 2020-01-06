from openflexure_microscope.common.labthings_core.utilities import (
    get_docstring,
    get_summary,
)
from flask import current_app


def description_from_view(view_class):
    methods = []
    for method_key in ["get", "post", "put", "delete"]:
        if hasattr(view_class, method_key):
            methods.append(method_key.upper())
    summary = get_summary(view_class)

    d = {"methods": methods, "description": summary}

    return d


def view_class_from_endpoint(endpoint: str):
    return current_app.view_functions[endpoint].view_class
