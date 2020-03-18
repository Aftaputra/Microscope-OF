from labthings.server.extensions import BaseExtension
from labthings.server.view import View
from labthings.server.decorators import ThingProperty, PropertySchema, use_args
from labthings.server import fields
from labthings.server.find import find_component
from labthings.core.utilities import path_relative_to

from openflexure_microscope.paths import settings_file_path, check_rw
from openflexure_microscope.config import OpenflexureSettingsFile
from openflexure_microscope.camera.base import BASE_CAPTURE_PATH
from openflexure_microscope.camera.capture import build_captures_from_exif

from openflexure_microscope.api.utilities.gui import build_gui

from flask import abort, url_for
import logging
import os
import psutil

from sys import platform


class CustomElementExtension(BaseExtension):
    def __init__(self):
        BaseExtension.__init__(
            self,
            "org.openflexure.customelement",
            description="Testing HTML components in an extension",
            static_folder=path_relative_to(__file__, "static"),
        )

        # Register the on_microscope function to run when the microscope is attached
        self.on_component("org.openflexure.microscope", self.on_microscope)

    def on_microscope(self, microscope_obj):
        """Function to automatically call when the parent LabThing has a microscope attached."""
        logging.debug(f"CustomElementExtension found microscope {microscope_obj}")


customelement_extension_v2 = CustomElementExtension()


def wc_func():
    return {
        "href": customelement_extension_v2.static_file_url("my-custom-element.min.js"),
        "name": "my-custom-element",
    }


def gui_func():
    return {"icon": "pets", "title": "Element", "viewPanel": "stream", "wc": wc_func()}


customelement_extension_v2.add_meta("wc", wc_func)
customelement_extension_v2.add_meta(
    "gui", build_gui(gui_func, customelement_extension_v2)
)
