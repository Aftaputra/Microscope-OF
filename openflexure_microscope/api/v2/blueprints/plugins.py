from openflexure_microscope.plugins import PluginLoader, MicroscopePlugin
from openflexure_microscope.api.views import MicroscopeViewPlugin

from flask import Blueprint, jsonify, url_for
from openflexure_microscope.api.views import MicroscopeView

import copy
import logging
import warnings


def plugins_representation(plugin_loader_object: PluginLoader):
    """
    Generate a dictionary representation of all plugins, including Flask route URLs

    Args:
        plugin_loader_object (:py:class:`openflexure_microscope.plugins.PluginLoader`): Microscope plugin loader

    Returns:
        dict: Dictionary representation of all plugins
    """
    plugins = []

    for plugin in plugin_loader_object.active:
        logging.debug(f"Representing plugin {plugin._name}")
        d = {
            "name": plugin._name,
            "plugin": str(plugin),
            "views": {},
            "form": plugin.form,
        }

        for view_id, view in plugin.views.items():
            logging.debug(f"Representing view {view_id}")
            uri = url_for(f"v2_plugins_blueprint.{view_id}")
            # Make links dictionary if it doesn't yet exist
            view_d = {
                "links": {"self": uri}
            }

            d["views"][view_id] = view_d

        plugins.append(d)

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
        return jsonify(plugins_representation(self.microscope.plugins))


def construct_blueprint(microscope_obj):

    blueprint = Blueprint("v2_plugins_blueprint", __name__)

    # Create a base route to return plugin API forms, if any exist
    blueprint.add_url_rule(
        "/", view_func=PluginFormAPI.as_view("plugins", microscope=microscope_obj)
    )

    all_routes = []

    # For each plugin attached to the microscope object
    for plugin in microscope_obj.plugins.active:

        for plugin_view_id, plugin_view in plugin.views.items():
            # Add route to the plugins blueprint
            blueprint.add_url_rule(
                plugin_view["rule"],
                view_func=plugin_view["view"].as_view(
                    plugin_view_id,
                    microscope=microscope_obj,
                    plugin=plugin,
                ),
            )

    return blueprint
