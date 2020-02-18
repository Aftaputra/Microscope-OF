from labthings.server.extensions import BaseExtension
from labthings.server.view import View
from labthings.server.decorators import ThingProperty, PropertySchema
from labthings.server import fields
from labthings.server.find import find_component

from openflexure_microscope.paths import settings_file_path, check_rw
from openflexure_microscope.config import OpenflexureSettingsFile
from openflexure_microscope.camera.base import BASE_CAPTURE_PATH

from flask import abort
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


def set_current_location(camera, location: str):
    if not os.path.isdir(location):
        os.makedirs(location)
    return camera.paths.update({"default": location})


def get_default_location():
    return BASE_CAPTURE_PATH


def get_all_locations():
    locations = {}
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

        # We'll store a reference to a camera object, who's capture paths will be modified
        self.camera = None

        self.initial_location = get_default_location()

        # Register the on_microscope function to run when the microscope is attached
        self.on_component("org.openflexure.microscope", self.on_microscope)

    @property
    def preferred(self):
        return self._preferred

    @preferred.setter
    def preferred(self, new_path_key: str):
        if not new_path_key in self.get_locations().keys():
            raise KeyError(f"No location named {new_path_key}")
        self._preferred = new_path_key

    def on_microscope(self, microscope_obj):
        """Function to automatically call when the parent LabThing has a microscope attached."""
        logging.debug(f"Autostorage extension found microscope {microscope_obj}")
        if hasattr(microscope_obj, "camera"):
            logging.debug(f"Autostorage extension bound to camera {self.camera}")

            # Store a reference to the camera
            self.camera = microscope_obj.camera
            # Store the initial storage location
            self.initial_location = get_current_location(self.camera)

            # If preferred path does not exist, or cannot be written to
            if not (
                os.path.isdir(self.initial_location) and check_rw(self.initial_location)
            ):
                logging.error(
                    f"Preferred capture path {self.initial_location} is missing or cannot be written to. Restoring defaults."
                )
                # Reset the storage location to default
                set_current_location(self.camera, get_default_location())

            logging.debug(self.get_locations())

    def get_locations(self):
        if self.camera:
            locations = get_all_locations()

            current_location = get_current_location(self.camera)
            if current_location not in locations.values():
                locations.update({"Custom": current_location})
            # Add location from the cameras settings file
            return locations
        else:
            return {}

    def get_preferred_key(self):
        current = get_current_location(self.camera)
        locations = self.get_locations()

        matches = [k for k, v in locations.items() if v == current]

        if len(matches) > 1:
            logging.warning(
                "Multiple path matches found. Weird, but carrying on using zeroth."
            )

        return matches[0]

    def set_preferred_key(self, new_path_key: str):
        if not new_path_key in self.get_locations().keys():
            raise KeyError(f"No location named {new_path_key}")

        location = self.get_locations().get(new_path_key)
        set_current_location(self.camera, location)


autostorage_extension_v2 = AutostorageExtension()


@ThingProperty
class GetLocationsView(View):
    def get(self):
        global autostorage_extension_v2

        return autostorage_extension_v2.get_locations()


@ThingProperty
@PropertySchema(fields.String(required=True, example="Default"))
class PreferredLocationView(View):
    def get(self):
        global autostorage_extension_v2

        return autostorage_extension_v2.get_preferred_key()

    def post(self, new_path_key):
        global autostorage_extension_v2
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to autofocus.")

        autostorage_extension_v2.set_preferred_key(new_path_key)
        microscope.save_settings()


autostorage_extension_v2.add_view(GetLocationsView, "list-locations")
autostorage_extension_v2.add_view(PreferredLocationView, "location")
