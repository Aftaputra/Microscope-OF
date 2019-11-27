import random
import time
import os
import json
from openflexure_microscope.devel import MicroscopePlugin, update_task_progress

from .api import DoAPI


class DynamicExamplePlugin(MicroscopePlugin):
    """
    An example plugin using a comprehensive form
    """

    api_views = {"/do": DoAPI}

    def __init__(self):
        MicroscopePlugin.__init__(self)

        self.val_int = 0
        self.val_str = "Hello"

        self.set_gui(self.dynamic_form)

    def dynamic_form(self):
        return {
            "id": "test-plugin",
            "icon": "pets",
            "forms": [
                {
                    "name": "Simple request",
                    "isCollapsible": False,
                    "isTask": False,
                    "selfUpdate": True,
                    "route": "/do",
                    "submitLabel": "Do things",
                    "schema": [
                        {
                            "fieldType": "numberInput",
                            "name": "val_int",
                            "label": "Number value",
                            "minValue": 0,
                        },
                        {
                            "fieldType": "htmlBlock",
                            "name": "html_block",
                            "content": f"<i>Value is: </i><br>{self.val_int}.",
                        },
                    ],
                }
            ],
        }
