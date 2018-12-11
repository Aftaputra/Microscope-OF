import importlib
import os
import warnings
import logging

MAIN_MODULE = '__init__'
HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_PLUGIN_PATH = os.path.join(HERE, 'default')


def search_plugin_dirs(plugin_paths, include_default=True):
    """
    Search through, and load from, a list of plugin directories.

    Args:
        plugin_paths (list): List of strings of plugin directories.
        include_default (bool): Also load plugins from the module default directory (DEFAULT_PLUGIN_PATH)
    """
    global DEFAULT_PLUGIN_PATH

    if include_default:  # If including default plugins
        plugin_paths.append(DEFAULT_PLUGIN_PATH)  # Add default directory to the search paths

    logging.debug(plugin_paths)

    plugins = []  # List of loaded plugins
    for plugin_dir in plugin_paths:  # For each plugin directory
        logging.debug("Searching {}".format(plugin_dir))
        plugins.extend(find_plugins(plugin_dir))  # Find plugin folders, and load into list

    return plugins


def find_plugins(plugin_dir):
    """
    Find all plugins residing within a directory

    Args:
        plugin_dir (str): String of directory to be searched
    """
    plugins = []
    plugins_folders = os.listdir(plugin_dir)

    loader_details = (
        importlib.machinery.SourceFileLoader,
        importlib.machinery.SOURCE_SUFFIXES
    )

    for i in plugins_folders:
        plugin_folder = os.path.join(plugin_dir, i)
        logging.info(plugin_folder)

        if not os.path.isdir(plugin_folder):
            continue
        if not MAIN_MODULE + '.py' in os.listdir(plugin_folder):
            continue

        module_spec = importlib.machinery.FileFinder(plugin_folder, loader_details).find_spec(MAIN_MODULE)

        plugins.append(module_spec)
    return plugins


def load_plugin(module_spec):
    """
    Load a source file from a given spec.

    Args:
        module_spec: Module spec of module to be returned
    """
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


class PluginMount(object):
    """
    A mount-point for all loaded plugins. Attaches to a Microscope object.

    Args:
        parent (:py:class:`openflexure_microscope.microscope.Microscope`): The parent Microscope object to attach to.
    """
    def __init__(self, parent):
        self.parent = parent
        print("Creating plugin mount")

    def attach(self, plugin_module):
        """
        Attach a MicroscopePlugin instance to the plugin mount.

        Args:
            plugin_module: A loaded module to be attached. Module can be loaded using :py:meth:`openflexure_microscope.plugins.load_plugin`
        """
        if not hasattr(plugin_module, 'PLUGINS') or not isinstance(plugin_module.PLUGINS, dict):
            raise Exception("No falid PLUGINS dictionary found in {}".format(plugin_module))

        for plugin_name, plugin_class in plugin_module.PLUGINS.items():

            plugin_object = plugin_class()
            if hasattr(self, plugin_name):
                warnings.warn("A plugin named {} has already been loaded. Skipping {}.".format(plugin_name, plugin_class))
            else:
                setattr(self, plugin_name, plugin_object)

                # Grant plugin access to the hardware
                assert(isinstance(plugin_object, MicroscopePlugin))
                plugin_object.microscope = self.parent

                print("Adding plugin: {}".format(plugin_name))


class MicroscopePlugin():
    """
    Parent class for all microscope plugins.

    Initially only defines an empty object for microscope. All plugins
    must be an instance of this class to successfully attach to PluginMount.
    """
    def __init__(self):
        self.microscope = None  #: :py:class:`openflexure_microscope.microscope.Microscope`: Microscope object
