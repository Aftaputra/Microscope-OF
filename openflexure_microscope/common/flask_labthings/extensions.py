import logging
import collections
import copy

from importlib import util
import sys

from openflexure_microscope.common.labthings_core.utilities import get_docstring
from openflexure_microscope.utilities import camel_to_snake, snake_to_spine


class BaseExtension:
    """
    Parent class for all extensions.

    Handles binding route views and forms.
    """

    def __init__(self, name: str, description=""):
        self._views = (
            {}
        )  # Key: Full, Python-safe ID. Val: Original rule, and view class
        self._rules = {}  # Key: Original rule. Val: View class
        self._gui = None

        self._cls = str(self)  # String description of extension instance

        self.actions = []
        self.properties = []

        self.name = name
        self.description = get_docstring(self)

        self.methods = {}

    @property
    def views(self):
        return self._views

    def add_view(self, view_class, rule, **kwargs):
        # Remove all leading slashes from view route
        cleaned_rule = rule
        while cleaned_rule[0] == "/":
            cleaned_rule = cleaned_rule[1:]

        # Expand the rule to include extension name
        full_rule = "/{}/{}".format(self._name_uri_safe, cleaned_rule)

        view_id = cleaned_rule.replace("/", "_").replace("<", "").replace(">", "")

        # Create a Python-safe route ID
        logging.debug(view_id)

        # Store route information in a dictionary
        d = {"rule": full_rule, "view": view_class, "kwargs": kwargs}

        # Add view to private views dictionary
        self._views[view_id] = d
        # Store the rule expansion information
        self._rules[rule] = self._views[view_id]

    def register_action(self, view_class):
        self.actions.append(view_class)

    def register_property(self, view_class):
        self.properties.append(view_class)

    @property
    def gui(self):
        print(self._gui)
        # Handle missing/no GUI
        if not self._gui:
            return None
        # Handle GUI as a dictionary-returning callable function
        elif isinstance(self._gui, collections.Callable):
            api_gui = self._gui()
        # Handle GUI as a static dictionary
        elif isinstance(self._gui, dict):
            api_gui = copy.deepcopy(self._gui)
        # Handle borked GUI
        else:
            raise ValueError(
                "GUI must be a dictionary, or a dictionary-returning function with no arguments."
            )

        api_gui["id"] = self._name

        if "forms" in api_gui and isinstance(api_gui["forms"], list):
            for form in api_gui["forms"]:
                if "route" in form and form["route"] in self._rules.keys():
                    form["route"] = self._rules[form["route"]]["rule"]
                else:
                    logging.warn(
                        "No valid expandable route found for {}".format(form["route"])
                    )
        return api_gui

    def set_gui(self, form_dictionary: dict):
        self._gui = form_dictionary

    @property
    def _name(self):
        return self.name

    @property
    def _name_python_safe(self):
        name = camel_to_snake(self._name)  # Camel to snake
        name = name.replace(" ", "_")  # Spaces to snake
        return name

    @property
    def _name_uri_safe(self):
        return snake_to_spine(self._name_python_safe)

    def add_method(self, method, method_name):
        self.methods[method_name] = method

        if not hasattr(self, method_name):
            setattr(self, method_name, method)
        else:
            logging.warning(
                "Unable to bind method to extension. Method name already exists."
            )


def find_extensions(extension_path, module_name="extensions"):
    logging.debug(f"Loading extensions from {extension_path}")

    spec = util.spec_from_file_location(module_name, extension_path)
    mod = util.module_from_spec(spec)
    sys.modules[spec.name] = mod

    spec.loader.exec_module(mod)

    if hasattr(mod, "__extensions__"):
        return mod.__extensions__
    else:
        return None
