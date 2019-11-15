from flask import Blueprint, url_for, jsonify
from sys import platform

from . import camera, stage, system

_actions = {
    "capture": {
        "rule": "/camera/capture/",
        "view_class": camera.CaptureAPI,
        "description": "Take a single still capture",
        "conditions": True,
    },
    "preview_start": {
        "rule": "/camera/preview/start",
        "view_class": camera.GPUPreviewStartAPI,
        "description": "Start the on-board GPU preview",
        "conditions": True,
    },
    "preview_stop": {
        "rule": "/camera/preview/stop",
        "view_class": camera.GPUPreviewStopAPI,
        "description": "Stop the on-board GPU preview",
        "conditions": True,
    },
    "move": {
        "rule": "/stage/move/",
        "view_class": stage.MoveStageAPI,
        "description": "Move the microscope stage",
        "conditions": True,
    },
    "shutdown": {
        "rule": "/system/shutdown/",
        "view_class": system.ShutdownAPI,
        "description": "Shutdown the device",
        "conditions": (platform == "linux"),
    },
    "reboot": {
        "rule": "/system/reboot/",
        "view_class": system.RebootAPI,
        "description": "Reboot the device",
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
            "description": action["description"],
            "rule": action["rule"],
            "view_class": str(action["view_class"]),
        }

        actions[name] = d

    return actions


def construct_blueprint(microscope_obj):
    global _actions

    blueprint = Blueprint("actions_blueprint", __name__)

    # For each enabled action route defined in our dictionary above
    for name, action in enabled_actions().items():
        # Add the action to our blueprint
        blueprint.add_url_rule(
            action["rule"],
            view_func=action["view_class"].as_view(name, microscope=microscope_obj),
        )

    @blueprint.route("/")
    def representation():
        return jsonify(actions_representation())

    return blueprint
