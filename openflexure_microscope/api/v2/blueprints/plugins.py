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

    print(plugin_loader_object.active)

    for plugin in plugin_loader_object.active:
        logging.info(f"Representing plugin {plugin._name}")
        d = {
            "name": plugin._name,
            "plugin": str(plugin),
            "views": {},
            "form": plugin.form,
        }

        for view_id, view in plugin.views.items():
            logging.info(f"Representing view {view_id}")
            uri = url_for(f"v2_plugins_blueprint.{view_id}")
            # Make links dictionary if it doesn't yet exist
            view_d = {
                "links": {"self": uri}
            }

            d["views"][view_id] = view_d

        print("\n")
        print(d)
        print("\n")
        plugins.append(d)

    print(plugins)
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

            """
            # If plugin includes an API form
            if hasattr(plugin_obj, "api_form") and isinstance(
                plugin_obj.api_form, dict
            ):
                # TODO: We deep copy this to avoid clashing between API versions. Can be removed when v1 is removed.
                api_form_info = copy.deepcopy(plugin_obj.api_form)
                api_form_info["id"] = plugin_name
                if "forms" in api_form_info and isinstance(
                    api_form_info["forms"], list
                ):
                    for form in api_form_info["forms"]:
                        if "route" in form and form["route"] in expanded_routes.keys():
                            form["route"] = expanded_routes[form["route"]]
                        else:
                            logging.warn(
                                "No valid expandable route found for {}".format(
                                    form["route"]
                                )
                            )

                # Store the complete form in Microscope().plugin.form
                plugin_representation["form"] = api_form_info
                print(microscope_obj.plugins.forms)
            """

    return blueprint
