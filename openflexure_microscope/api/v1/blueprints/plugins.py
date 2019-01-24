from openflexure_microscope.api.v1.views import MicroscopeViewPlugin

from flask import Response, Blueprint, jsonify

import logging, warnings


def construct_blueprint(microscope_obj, plugin_paths=[], include_default=True):

    blueprint = Blueprint('plugin_blueprint', __name__)

    all_routes = []

    # For each plugin attached to the microscope object
    for plugin_name, plugin_obj in microscope_obj.plugin.plugins:

        # If plugin contains valid endpoints
        if hasattr(plugin_obj, 'api_views') and isinstance(plugin_obj.api_views, dict):

            # For each defined endpoint
            for view_route, view_class in plugin_obj.api_views.items():

                # Remove all leading slashes from view route
                while view_route[0] == '/':
                    view_route = view_route[1:]

                # Construct a full view route from the plugin name
                full_view_route = "/{}/{}".format(plugin_name, view_route)
                logging.debug(full_view_route)

                # Check if endpoint name clashes
                if full_view_route not in all_routes and issubclass(view_class, MicroscopeViewPlugin):
                    # Add route to main route dictionary
                    all_routes.append(full_view_route)

                    # Add route to the plugins blueprint
                    blueprint.add_url_rule(
                        full_view_route,
                        view_func=view_class.as_view(
                            'plugin_{}'.format(full_view_route).replace('/', '_'),
                            microscope=microscope_obj,
                            plugin=plugin_obj
                        )
                    )

                else:
                    warnings.warn(
                        "An endpoint /{} has already been loaded. Skipping {}.".format(
                            full_view_route,
                            view_class
                        )
                    )

        else:
            warnings.warn(
                "No valid 'api_views' dictionary found in {}".format(plugin_obj)
            )

    return(blueprint)
