"""
Top-level representation of attached and enabled plugins
"""

from openflexure_microscope.api.views import MicroscopeViewPlugin
from openflexure_microscope.utilities import get_docstring, description_from_view
from openflexure_microscope.api.utilities import blueprint_for_module

from openflexure_microscope.common.labthings.plugins import find_plugins
from openflexure_microscope.config import USER_PLUGINS_PATH

from flask import Blueprint, jsonify, url_for
from openflexure_microscope.api.views import MicroscopeView

import copy
import logging
import warnings

_plugins = find_plugins(USER_PLUGINS_PATH)
print(_plugins)


def plugins_representation(plugin_list):
    """
    Generate a dictionary representation of all plugins, including Flask route URLs

    Args:
        plugin_loader_object (:py:class:`openflexure_microscope.plugins.PluginLoader`): Microscope plugin loader

    Returns:
        dict: Dictionary representation of all plugins
    """
    plugins = {}

    for plugin in plugin_list:
        logging.debug(f"Representing plugin {plugin._name}")
        d = {
            "python_name": plugin._name_python_safe,
            "plugin": str(plugin),
            "views": {},
            "gui": plugin.gui,
            "description": get_docstring(plugin),
        }

        for view_id, view_data in plugin.views.items():
            logging.debug(f"Representing view {view_id}")
            uri = url_for(f"v2_plugins_blueprint.plugins") + view_data["rule"][1:]
            # uri = view_data["rule"]
            # Make links dictionary if it doesn't yet exist
            view_d = {"links": {"self": uri}}

            view_d.update(description_from_view(view_data["view"]))

            d["views"][view_id] = view_d

        plugins[plugin._name] = d

    return plugins


class PluginFormAPI(MicroscopeView):
    def get(self):
        """
        Return the current plugin forms

        .. :quickref: Plugin; Get forms

        Returns an array of present plugin forms (describing plugin user interfaces.)
        Please note, this is *not* a list of all enabled plugins, only those with associated
        user interface forms.

        A complete list of enabled plugins can be found in the microscope state.

        """
        global _plugins
        return jsonify(plugins_representation(_plugins))


def construct_blueprint(microscope_obj):

    blueprint = blueprint_for_module(__name__)

    for plugin_obj in _plugins:
        for plugin_view_id, plugin_view in plugin_obj.views.items():
            # Add route to the plugins blueprint
            blueprint.add_url_rule(
                plugin_view["rule"],
                view_func=plugin_view["view"].as_view(
                    f"{plugin_obj._name_python_safe}_{plugin_view_id}"
                ),
                **plugin_view["kwargs"],
            )

    # Create a base route to return plugin API forms, if any exist
    blueprint.add_url_rule(
        "/", view_func=PluginFormAPI.as_view("plugins", microscope=microscope_obj)
    )

    # For each plugin attached to the microscope object
    for plugin in microscope_obj.plugins.active:

        for plugin_view_id, plugin_view in plugin.views.items():
            # Add route to the plugins blueprint
            blueprint.add_url_rule(
                plugin_view["rule"],
                view_func=plugin_view["view"].as_view(
                    f"{plugin._name_python_safe}_{plugin_view_id}",
                    microscope=microscope_obj,
                    plugin=plugin,
                ),
                **plugin_view["kwargs"],
            )

    return blueprint
