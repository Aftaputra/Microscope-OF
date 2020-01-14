"""
Top-level representation of enabled actions
"""

from . import camera, stage, system

from openflexure_microscope.common.flask_labthings.view import View
from openflexure_microscope.common.flask_labthings.find import current_labthing
from openflexure_microscope.common.flask_labthings.utilities import description_from_view
from openflexure_microscope.common.flask_labthings.decorators import Tag

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


@Tag("actions")
class ActionsView(View):
    def get(self):
        """
        List of enabled default API actions.

        This list does not include any actions added by LabThings extensions, only
        those part of the default OpenFlexure Microscope API.
        """
        global _actions

        actions = {}
        for name, action in enabled_root_actions().items():
            d = {
                "links": {
                    "self": {
                        "href": current_labthing().url_for(action["view_class"]),
                        "mimetype": "application/json",
                        **description_from_view(action["view_class"])
                    }
                },
                "rule": action["rule"],
                "view_class": str(action["view_class"]),
            }

            actions[name] = d

        return actions
