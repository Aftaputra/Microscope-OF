from openflexure_microscope.api.utilities import parse_payload, get_from_payload, gen, get_bool
from openflexure_microscope.api.v1.views import MicroscopeView

from openflexure_microscope.plugins import load_plugin, search_plugin_dirs

from flask import Response, Blueprint, jsonify

import logging, warnings


def add_endpoints(plugin_module, endpoint_dict):
    """
    Fetch valid endpoints from a plugin_module

    Args:
        plugin_module: A loaded module to be attached. Module can be loaded using :py:meth:`openflexure_microscope.plugins.load_plugin`
    """
    if hasattr(plugin_module, 'ENDPOINTS') and isinstance(plugin_module.ENDPOINTS, dict):  # If plugin contains valid endpoints

        for endpoint_name, endpoint_class in plugin_module.ENDPOINTS.items():  # For each defined endpoint

            if endpoint_name in endpoint_dict:  # Check if endpoint name clashes
                warnings.warn("An endpoint /{} has already been loaded. Skipping {}.".format(endpoint_name, endpoint_class))
            else:
                endpoint_dict[endpoint_name] = endpoint_class  # Add endpoint to main endpoint dictionary
    else:
        warnings.warn("No valid ENDPOINTS dictionary found in {}".format(plugin_module))


def construct_blueprint(microscope_obj, plugin_paths=[], include_default=True):

    blueprint = Blueprint('plugin_blueprint', __name__)

    logging.debug("Attaching plugins...")
    plugins_list = search_plugin_dirs(plugin_paths, include_default=include_default)

    endpoint_dict = {}  # Store all endpoints

    for plugin_file in plugins_list:
        plugin_module = load_plugin(plugin_file)
        add_endpoints(plugin_module, endpoint_dict)

    for endpoint_name, endpoint_class in endpoint_dict.items():  # For each valid endpoint

        blueprint.add_url_rule(
            '/{}'.format(endpoint_name),
            view_func=endpoint_class.as_view('plugin_{}'.format(endpoint_name), microscope=microscope_obj)
        )

    return(blueprint)
