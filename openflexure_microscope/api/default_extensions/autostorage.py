from labthings.server.extensions import BaseExtension
from openflexure_microscope.paths import settings_file_path, check_rw
from openflexure_microscope.config import OpenflexureSettingsFile
from openflexure_microscope.camera.base import BASE_CAPTURE_PATH

import logging
import os
import psutil

from sys import platform


AS_SETTINGS_PATH = settings_file_path("autostorage_settings.json")


def get_partitions():
    return [disk.mountpoint for disk in psutil.disk_partitions() if "rw" in disk.opts]


def get_permissive_partitions():
    return [partition for partition in get_partitions() if check_rw(partition)]


def get_permissive_locations():
    return [
        (partition, os.path.join(partition, "openflexure", "data", "micrographs"))
        for partition in get_permissive_partitions()
    ]


def get_current_location(camera):
    return camera.paths.get("default")


def get_default_location():
    return BASE_CAPTURE_PATH


def get_all_locations(camera):
    locations = {"System": get_current_location(camera)}
    # If default is not already listed (e.g. if it's currently set)
    if get_default_location() not in locations.values():
        locations["Default"] = get_default_location()

    for ppartition, plocation in get_permissive_locations():
        pdrive = os.path.splitdrive(plocation)[0]
        if not (
            pdrive  # If path actually has a drive (basically just Windows?)
            and any(  # And shares a common drive with an existing location
                [
                    pdrive == os.path.splitdrive(location)[0]
                    for location in locations.values()
                ]
            )
        ):
            locations[ppartition] = plocation

    # Strip out Nones
    return {k: v for k, v in locations.items() if v}


class CaptureStorageLocation:
    def __init__(self, mountpoint):
        pass


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

            logging.debug(self.get_locations())

    def get_locations(self):
        if self.camera:
            return get_all_locations(self.camera)
        else:
            return []


autostorage_extension_v2 = AutostorageExtension()
