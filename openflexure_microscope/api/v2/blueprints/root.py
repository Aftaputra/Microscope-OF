from flask import Blueprint, jsonify, url_for
from openflexure_microscope import Microscope
from openflexure_microscope.api.views import MicroscopeView

from openflexure_microscope.utilities import get_docstring, bottom_level_name
from openflexure_microscope.api.utilities import blueprint_name_for_module
from openflexure_microscope.api.v2.blueprints import settings, status, plugins, captures, actions, stream

# List of submodules containing create_blueprint methods using standard blueprint_for_module naming
_root_blueprint_modules = [settings, status, plugins, captures, actions, stream]

def root_representation():
    """
    Generate a dictionar representation of all top-level blueprint rules
    """
    global _root_blueprint_modules
    d = {}

    for blueprint_module in _root_blueprint_modules:
        module_short_name = bottom_level_name(blueprint_module)
        blueprint_name = blueprint_name_for_module(blueprint_module.__name__)

        d[module_short_name] = {
            "name": blueprint_module.__name__,
            "description": get_docstring(blueprint_module),
            "links": {"self": url_for(f"{blueprint_name}.{module_short_name}")}
        }

    return d


class RootAPI(MicroscopeView):
    def get(self):

        return jsonify(root_representation())


def construct_blueprint(microscope_obj):
    blueprint = Blueprint("root_blueprint", __name__)

    blueprint.add_url_rule(
        "/", view_func=RootAPI.as_view("root_repr", microscope=microscope_obj)
    )
    return blueprint
