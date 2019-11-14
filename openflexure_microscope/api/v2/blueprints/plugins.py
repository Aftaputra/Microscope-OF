from openflexure_microscope.plugins import PluginLoader, MicroscopePlugin
from openflexure_microscope.api.views import MicroscopeViewPlugin

from flask import Blueprint, jsonify
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
        d = {
            "name": plugin["name"],
            "plugin": str(plugin["plugin"]),
            "routes": plugin["routes"],
            "form": plugin["form"]
        }
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

    blueprint = Blueprint("plugins_blueprint", __name__)

    # Create a base route to return plugin API forms, if any exist
    blueprint.add_url_rule(
        "/",
        view_func=PluginFormAPI.as_view("plugins", microscope=microscope_obj),
    )

    all_routes = []

    # For each plugin attached to the microscope object
    for plugin_representation in microscope_obj.plugins.active:

        plugin_obj = plugin_representation["plugin"]
        plugin_name = plugin_representation["name"]

        # If plugin contains valid endpoints
        if hasattr(plugin_obj, "api_views") and isinstance(plugin_obj.api_views, dict):

            # We'll keep a record of how each route was expanded
            expanded_routes = {}

            # For each defined endpoint
            for view_route, view_class in plugin_obj.api_views.items():

                # Remove all leading slashes from view route
                cleaned_route = view_route
                while cleaned_route[0] == "/":
                    cleaned_route = cleaned_route[1:]

                # Construct a full view route from the plugin name
                full_view_route = "/{}/{}".format(plugin_name, cleaned_route)
                logging.debug(full_view_route)

                # Record how the view_route got expanded
                expanded_routes[view_route] = full_view_route

                # Check if endpoint name clashes
                if full_view_route not in all_routes and issubclass(
                    view_class, MicroscopeViewPlugin
                ):
                    # Add route to main route dictionary
                    all_routes.append(full_view_route)

                    # Create a Python-safe name for the route
                    plugin_route_id = "plugin{}".format(full_view_route).replace(
                        "/", "_"
                    )

                    # Add route to the plugins blueprint
                    blueprint.add_url_rule(
                        full_view_route,
                        view_func=view_class.as_view(
                            plugin_route_id,
                            microscope=microscope_obj,
                            plugin=plugin_obj,
                        ),
                    )

                    # Add route to the plugin representation dictionary
                    plugin_representation["routes"].append(full_view_route)

                else:
                    warnings.warn(
                        "An endpoint /{} has already been loaded. Skipping {}.".format(
                            full_view_route, view_class
                        )
                    )

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

        else:
            warnings.warn(
                "No valid 'api_views' dictionary found in {}".format(plugin_obj)
            )
    return blueprint
