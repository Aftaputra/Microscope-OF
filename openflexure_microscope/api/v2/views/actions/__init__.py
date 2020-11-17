"""
Top-level representation of enabled actions
"""
from flask import url_for
from labthings import current_labthing
from labthings.utilities import description_from_view
from labthings.views import View

from . import camera, stage, system

_actions = {
    "capture": {
        "rule": "/camera/capture/",
        "view_class": camera.CaptureAPI,
        "conditions": True,
    },
    "ramCapture": {
        "rule": "/camera/ram-capture/",
        "view_class": camera.RAMCaptureAPI,
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


def enabled_root_actions():
    return {k: v for k, v in _actions.items() if v["conditions"]}
