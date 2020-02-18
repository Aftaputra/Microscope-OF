from labthings.server.extensions import BaseExtension
from openflexure_microscope.paths import settings_file_path
from openflexure_microscope.config import OpenflexureSettingsFile

import logging

AS_SETTINGS_PATH = settings_file_path("autostorage_settings.json")


class AutostorageExtension(BaseExtension):
    def __init__(self):
        BaseExtension.__init__(
            self,
            "org.openflexure.autostorage",
            version="2.0.0-beta.1",
            description="Handle switching capture storage devices",
        )

        self.settings = OpenflexureSettingsFile(
            AS_SETTINGS_PATH, defaults={"preferred": None}
        )

        # We'll store a reference to a camera object, who's capture paths will be modified
        self.camera = None

        # Register the on_microscope function to run when the microscope is attached
        self.on_component("org.openflexure.microscope", self.on_microscope)

    def on_microscope(self, microscope_obj):
        """Function to automatically call when the parent LabThing has a microscope attached."""
        logging.debug(f"Autostorage extension found microscope {microscope_obj}")
        if hasattr(microscope_obj, "camera"):
            self.camera = microscope_obj.camera
            logging.debug(f"Autostorage extension bound to camera {self.camera}")


autostorage_extension_v2 = AutostorageExtension()
