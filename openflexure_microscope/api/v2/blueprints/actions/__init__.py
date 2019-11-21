"""
Top-level representation of enabled actions
"""

from flask import Blueprint, url_for, jsonify
from sys import platform

from openflexure_microscope.api.utilities import blueprint_for_module
from openflexure_microscope.utilities import get_docstring, description_from_view
from openflexure_microscope.api.views import MicroscopeView

from . import camera, stage, system


class ActionsAPI(MicroscopeView):
    def get(self):
        return jsonify(actions_representation())


_actions = {
    "capture": {
        "rule": "/camera/capture/",
        "view_class": camera.CaptureAPI,
        "conditions": True,
    },
    "previewStart": {
        "rule": "/camera/preview/start",
        "view_class": camera.GPUPreviewStartAPI,
        "conditions": True,
    },
    "previewStop": {
        "rule": "/camera/preview/stop",
        "view_class": camera.GPUPreviewStopAPI,
        "conditions": True,
    },
    "move": {
        "rule": "/stage/move/",
        "view_class": stage.MoveStageAPI,
        "conditions": True,
    },
    "shutdown": {
        "rule": "/system/shutdown/",
        "view_class": system.ShutdownAPI,
        "conditions": (platform == "linux"),
    },
    "reboot": {
        "rule": "/system/reboot/",
        "view_class": system.RebootAPI,
        "conditions": (platform == "linux"),
    },
}


def enabled_actions():
    global _actions
    return {k: v for k, v in _actions.items() if v["conditions"]}


def actions_representation():
    global _actions

    actions = {}
    for name, action in enabled_actions().items():
        d = {
            "links": {"self": url_for(f".{name}")},
            "rule": action["rule"],
            "view_class": str(action["view_class"]),
        }

        d.update(description_from_view(action["view_class"]))

        actions[name] = d

    return actions


def construct_blueprint(microscope_obj):
    global _actions

    blueprint = blueprint_for_module(__name__)

    # For each enabled action route defined in our dictionary above
    for name, action in enabled_actions().items():
        # Add the action to our blueprint
        blueprint.add_url_rule(
            action["rule"],
            view_func=action["view_class"].as_view(name, microscope=microscope_obj),
        )

    blueprint.add_url_rule(
        "/", view_func=ActionsAPI.as_view("actions", microscope=microscope_obj)
    )

    return blueprint
