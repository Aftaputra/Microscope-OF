"""
Top-level representation of enabled actions
"""

from flask import Blueprint, url_for, jsonify

from openflexure_microscope.api.utilities import blueprint_for_module
from openflexure_microscope.utilities import get_docstring, description_from_view
from openflexure_microscope.api.views import MicroscopeView

from . import camera, stage, system

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
    "zeroStage": {
        "rule": "/stage/zero/",
        "view_class": stage.ZeroStageAPI,
        "conditions": True,
    },
    "shutdown": {
        "rule": "/system/shutdown/",
        "view_class": system.ShutdownAPI,
        "conditions": system.is_raspberrypi(),
    },
    "reboot": {
        "rule": "/system/reboot/",
        "view_class": system.RebootAPI,
        "conditions": system.is_raspberrypi(),
    },
}


def enabled_actions():
    global _actions
    return {k: v for k, v in _actions.items() if v["conditions"]}


def add_actions_to_labthing(labthing, prefix=""):
    """
    Add all capture resources to a labthing
    """
    for name, action in enabled_actions().items():
        view_class = action["view_class"]
        rule = action["rule"]
        labthing.add_resource(view_class, f"{prefix}/actions{rule}")
        labthing.register_action(view_class)
