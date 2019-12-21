from openflexure_microscope.common.labthings_core.utilities import get_docstring


def description_from_view(view_class):
    methods = []
    for method_key in ["get", "post", "put", "delete"]:
        if hasattr(view_class, method_key):
            methods.append(method_key.upper())
    brief_description = get_docstring(view_class).partition("\n")[0].strip()

    d = {"methods": methods, "description": brief_description}

    return d
