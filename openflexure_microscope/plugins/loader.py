import importlib
import copy
import os
import inspect
import logging

from openflexure_microscope.utilities import camel_to_snake, camel_to_spine
from openflexure_microscope.api.views import MicroscopeViewPlugin


class ConColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def module_from_file(plugin_path):
    # Expand environment variables in path string
    plugin_path = os.path.expandvars(plugin_path)
    # Expand user directory in path string
    plugin_path = os.path.expanduser(plugin_path)

    # Check if the path is to a file
    if not os.path.isfile(plugin_path):
        logging.warning(
            ConColors.FAIL
            + "No valid plugin found at {}.".format(plugin_path)
            + ConColors.ENDC
        )
        return None, None, None

    else:
        # Get name of plugin from the file
        plugin_name = os.path.splitext(os.path.basename(plugin_path))[0]

        plugin_spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        plugin_module = importlib.util.module_from_spec(plugin_spec)

        return plugin_spec, plugin_module, plugin_name


def check_module(module_path):
    """
    Used to check if a module exists, without ever importing it.

    This checks each nested level separately to avoid raising exceptions.
    For example, checking "mymodule.submodule.subsubmodule" will first 
    check if 'mymodule' exists, then if it does, it will check
    'mymodule.submodule', and so on.
    """
    module_split = module_path.split(".")
    spec_path = ""

    for module_level in module_split:
        spec_path += ".{}".format(module_level)
        spec_path = spec_path.strip(".")

        logging.debug("Checking {}".format(spec_path))

        # Try to find a module loader for the plugin path
        plugin_spec = importlib.util.find_spec(spec_path)

        # If plugin spec doesn't exist, return False early
        if plugin_spec is None:
            return False

    # If all checks pass, return True
    return True


def name_from_module(plugin_path):
    path_array = plugin_path.split(".")

    # Truncate namespace of default plugins
    if path_array[0:2] == ["openflexure_microscope", "plugins"]:
        path_array = path_array[2:]

    return "/".join(path_array)


def load_plugin_module(plugin_path):
    # If the loader was found (i.e. plugin probably exists)
    if check_module(plugin_path):
        try:
            plugin_module = importlib.import_module(plugin_path)
            plugin_name = name_from_module(plugin_path)
        except Exception as e:
            logging.warning("Error loading plugin.")
            logging.error(e)
            return None, None

    # If no loader was found, try finding a file from path
    else:
        plugin_spec, plugin_module, plugin_name = module_from_file(plugin_path)
        # If a valid plugin was found
        if plugin_spec and plugin_module:
            # Execute the module, so we have access to it
            plugin_spec.loader.exec_module(plugin_module)

    return plugin_module, plugin_name


def load_plugin_class(plugin_path, plugin_class_name):
    plugin_module, plugin_name = load_plugin_module(plugin_path)
    if plugin_module:
        # Now try to extract the class
        try:
            plugin_class = getattr(plugin_module, plugin_class_name)
        except AttributeError:
            logging.warning(
                ConColors.FAIL
                + "Class {} does not exist in plugin {}. Skipping.".format(
                    plugin_class_name, plugin_path
                )
                + ConColors.ENDC
            )
            return None, None
        else:
            return plugin_class, plugin_name
    else:
        return None, None


def class_from_map(plugin_map):
    plugin_arr = plugin_map.split(":")

    if not len(plugin_arr) == 2:
        logging.warning(
            ConColors.WARNING
            + "Malformed plugin map {}. Skipping.".format(plugin_map)
            + ConColors.ENDC
        )
        return None, None
    else:
        return load_plugin_class(*plugin_arr)


class PluginLoader(object):
    """
    A mount-point for all loaded plugins. Attaches to a Microscope object.

    Args:
        parent (:py:class:`openflexure_microscope.microscope.Microscope`): The parent Microscope object to attach to.
    """

    def __init__(self, parent):
        self.parent = parent
        self._plugins = []  # List of plugin objects
        self._legacy_plugins = {}  # DEPRECATED: Dictionary of plugins with old names
        self.forms = []  # List of plugin forms
        logging.info("Creating plugin mount")

    @property
    def state(self):
        # DEPRECATED
        logging.warning(
            "PluginMount.state is deprecated. Use PluginMount.active instead. State will be removed in a future version."
        )
        return list(self._legacy_plugins.keys())

    @property
    def active(self):
        return self._plugins

    def attach(self, plugin_map):
        """
        Attach a MicroscopePlugin instance to the plugin mount.

        Args:
            plugin_map (str): A plugin map describing the file or module to load a MicroscopePlugin child from. Maps should be in the format 'module.to.load:ClassName' or '/path/to/file:ClassName'.
        """
        plugin_class, plugin_name = class_from_map(plugin_map)

        if plugin_class is not None:

            logging.debug(f"Loading plugin class {plugin_class}, {plugin_name}")

            plugin_name_python_safe = plugin_name.replace("/", "_")

            if plugin_class and plugin_name:
                plugin_object = plugin_class()

                if hasattr(
                    self, plugin_name
                ):  # If a plugin with the same name is already attached.
                    logging.warning(
                        ConColors.WARNING
                        + "A plugin named {} has already been loaded. Skipping {}.".format(
                            plugin_name, plugin_map
                        )
                        + ConColors.ENDC
                    )

                elif isinstance(
                    plugin_object, BasePlugin
                ):  # If plugin_object is an instance of MicroscopePlugin
                    # Attach plugin_object to the plugin mount
                    setattr(self, plugin_name_python_safe, plugin_object)
                    # Store the plugin object, and it's properties
                    self._plugins.append(plugin_object)
                    # DEPRECATED: Store the plugin with it's old name
                    self._legacy_plugins[plugin_name_python_safe] = plugin_object

                    # Grant plugin access to the hardware
                    if isinstance(plugin_object, MicroscopePlugin):
                        plugin_object.microscope = self.parent

                    logging.info(
                        ConColors.OKGREEN
                        + "Plugin {} loaded as {}.".format(
                            plugin_map, plugin_object._name
                        )
                        + ConColors.ENDC
                    )

        else:
            logging.warning(f"Error loading plugin {plugin_map}. Moving on.")


class BasePlugin:
    """
    Parent class for all plugins.

    Handles binding route views and forms.
    """

    def __init__(self):
        self._views = (
            {}
        )  # Key: Full, Python-safe ID. Val: Original rule, and view class
        self._rules = {}  # Key: Original rule. Val: View class
        self._gui = None

        # If old api_views dictionary is found
        if hasattr(self, "api_views"):
            # Convert to new format
            self._convert_old_api_views()
        # If old api_form dictionary is found
        if hasattr(self, "api_form"):
            # Convert to new format
            self._convert_old_api_form()

    @property
    def views(self):
        return self._views

    def add_view(self, rule, view_class):
        # Remove all leading slashes from view route
        cleaned_rule = rule
        while cleaned_rule[0] == "/":
            cleaned_rule = cleaned_rule[1:]

        # Expand the rule to include plugin name
        full_rule = "/{}/{}".format(self._name_uri_safe, cleaned_rule)

        # Create a Python-safe route ID
        view_id = cleaned_rule.replace("/", "_")

        # Store route information in a dictionary
        d = {"rule": full_rule, "view": view_class}

        # Add view to private views dictionary
        self._views[view_id] = d
        # Store the rule expansion information
        self._rules[rule] = self._views[view_id]

    @property
    def gui(self):
        if not self._gui:
            return None

        api_gui = copy.deepcopy(self._gui)
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

    def _convert_old_api_views(self):
        for view_route, view_class in self.api_views.items():
            self.add_view(view_route, view_class)

    def _convert_old_api_form(self):
        self.set_gui(self.api_form)

    @property
    def _name(self):
        return self.__class__.__name__

    @property
    def _name_python_safe(self):
        return camel_to_snake(self._name)

    @property
    def _name_uri_safe(self):
        return camel_to_spine(self._name)

    def _full_name(self):
        module = self.__class__.__module__
        if module is None or module == str.__class__.__module__:
            return self.__class__.__name__  # Avoid reporting __builtin__
        else:
            return module + "." + self.__class__.__name__


class MicroscopePlugin(BasePlugin):
    """
    Parent class for all microscope plugins.

    Initially only defines an empty object for microscope. All plugins
    must be an instance of this class to successfully attach to PluginMount.
    """

    api_views = {}  # Initially empty dictionary of API views associated with the plugin

    def __init__(self):
        BasePlugin.__init__(self)
        self.microscope = (
            None
        )  #: :py:class:`openflexure_microscope.microscope.Microscope`: Microscope object
