from flask import Blueprint, jsonify, url_for
from openflexure_microscope import Microscope
from openflexure_microscope.api.views import MicroscopeView

def root_representation(microscope_obj: Microscope):
    d = {
        "settings": {
            "description": "Writeable settings for the microscope, and attached hardware",
            "links": {"self": url_for("v2_settings_blueprint.settings")}
        },
        "status": {
            "description": "Read-only status of the microscope, and attached hardware info",
            "links": {"self": url_for("v2_status_blueprint.status")}
        },
        "plugins": {
            "description": "Top-level representation of attached and enabled plugins",
            "links": {"self": url_for("v2_plugins_blueprint.plugins")}
        },
        "captures": {
            "description": "Top-level representation of all acquired captures",
            "links": {"self": url_for("v2_captures_blueprint.captures")}
        },
        "actions": {
            "description": "Top-level representation of enabled actions",
            "links": {"self": url_for("v2_actions_blueprint.actions")}
        },
    }

    return d


class RootAPI(MicroscopeView):
    def get(self):

        return jsonify(root_representation(self.microscope))


def construct_blueprint(microscope_obj):
    blueprint = Blueprint("root_blueprint", __name__)

    blueprint.add_url_rule(
        "/", view_func=RootAPI.as_view("root_repr", microscope=microscope_obj)
    )
    return blueprint
