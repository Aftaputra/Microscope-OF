from openflexure_microscope.common.labthings_core.utilities import (
    get_docstring,
    get_summary,
)


def description_from_view(view_class):
    methods = []
    for method_key in ["get", "post", "put", "delete"]:
        if hasattr(view_class, method_key):
            methods.append(method_key.upper())
    summary = get_summary(view_class)

    d = {"methods": methods, "description": summary}

    return d
