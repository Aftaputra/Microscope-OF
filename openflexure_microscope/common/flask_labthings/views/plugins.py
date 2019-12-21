"""
Top-level representation of attached and enabled plugins
"""

from openflexure_microscope.common.labthings_core.utilities import get_docstring
from ..utilities import description_from_view

from openflexure_microscope.common.flask_labthings.find import registered_plugins
from openflexure_microscope.common.flask_labthings.resource import Resource

from flask import jsonify, url_for

import logging


def plugins_representation(plugin_dict):
    """
    Generate a dictionary representation of all plugins, including Flask route URLs

    Args:
        plugin_dict (dict): Dictionary of plugin objects

    Returns:
        dict: Dictionary representation of all plugins
    """
    plugins = {}

    for plugin_name, plugin in plugin_dict.items():
        logging.debug(f"Representing plugin {plugin._name}")
        d = {
            "python_name": plugin._name_python_safe,
            "plugin": str(plugin),
            "links": {},
            "gui": plugin.gui,
            "description": get_docstring(plugin),
        }

        for view_id, view_data in plugin.views.items():
            uri = (
                url_for(f"PluginListResource", _external=True)
                + "/"
                + view_data["rule"][1:]
            )
            # Make links dictionary if it doesn't yet exist
            view_d = {"href": uri, **description_from_view(view_data["view"])}

            d["links"][view_id] = view_d

        plugins[plugin_name] = d

    return plugins


class PluginListResource(Resource):
    def get(self):
        """
        Return the current plugin forms

        .. :quickref: Plugin; Get forms

        Returns an array of present plugin forms (describing plugin user interfaces.)
        Please note, this is *not* a list of all enabled plugins, only those with associated
        user interface forms.

        A complete list of enabled plugins can be found in the microscope state.

        """
        return jsonify(plugins_representation(registered_plugins()))
