"""
Top-level representation of enabled actions
"""

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


def enabled_root_actions():
    global _actions
    return {k: v for k, v in _actions.items() if v["conditions"]}
