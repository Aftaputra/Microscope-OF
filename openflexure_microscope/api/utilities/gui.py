import copy
import logging
from functools import wraps


def expand_routes_from_dict(gui_description, extension_object):
    api_gui = copy.deepcopy(gui_description)
    if "forms" in gui_description and isinstance(api_gui["forms"], list):
        for form in api_gui["forms"]:
            if "route" in form and form["route"] in extension_object._rules.keys():
                form["route"] = extension_object._rules[form["route"]]["rule"]
            else:
                logging.warn(
                    "No valid expandable route found for {}".format(form["route"])
                )
    return api_gui


def expand_routes_from_func(func, extension_object):
    @wraps(func)
    def wrapped(*args, **kwargs):
        return expand_routes_from_dict(func(*args, **kwargs), extension_object)

    return wrapped


def expand_routes(gui_description, extension_object):
    # If given a function that generates a GUI dictionary
    if callable(gui_description):
        # Wrap in the route expander
        return expand_routes_from_func(gui_description, extension_object)
    # If given a dictionary directly
    elif isinstance(gui_description, dict):
        # Build a GUI generator function
        def gui_description_func():
            return gui_description

        # Wrap in the route expander
        return expand_routes_from_func(gui_description_func, extension_object)
    else:
        raise RuntimeError("GUI description must be a function or a dictionary")
