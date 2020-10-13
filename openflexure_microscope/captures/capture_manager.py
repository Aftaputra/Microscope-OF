import datetime
import logging
import os
import shutil
from collections import OrderedDict

from labthings import StrictLock

from openflexure_microscope.paths import data_file_path
from openflexure_microscope.utilities import entry_by_uuid

from .capture import CaptureObject, build_captures_from_exif

BASE_CAPTURE_PATH = data_file_path("micrographs")
TEMP_CAPTURE_PATH = os.path.join(BASE_CAPTURE_PATH, "tmp")


def last_entry(object_list: list):
    """Return the last entry of a list, if the list contains items."""
    if object_list:  # If any images have been captured
        return object_list[-1]  # Return the latest captured image
    else:
        return None


def generate_basename():
    """Return a default filename based on the capture datetime"""
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def generate_numbered_basename(obj_list: list) -> str:
    initial_basename = generate_basename()
    basename = initial_basename
    # Handle clashing
    iterator = 1
    while basename in [obj.basename for obj in obj_list]:
        basename = initial_basename + "_{}".format(iterator)
        iterator += 1

    return basename


class CaptureManager:
    def __init__(self):
        self.paths = {"default": BASE_CAPTURE_PATH, "temp": TEMP_CAPTURE_PATH}

        self.lock = StrictLock(timeout=1, name="Captures")

        # Capture data
        self.images = OrderedDict()
        self.videos = OrderedDict()

    # FILE MANAGEMENT

    def __enter__(self):
        """Create camera on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close camera stream on context exit."""
        self.close()

    def close(self):
        logging.info("Closing {}".format(self))
        # Close all StreamObjects
        for capture_list in [self.images.values(), self.videos.values()]:
            for stream_object in capture_list:
                stream_object.close()
        # Empty temp directory
        self.clear_tmp()

    def clear_tmp(self):
        """
        Removes all files in the temporary capture directories
        """

        if os.path.isdir(self.paths["temp"]):
            logging.info("Clearing {}...".format(self.paths["temp"]))
            shutil.rmtree(self.paths["temp"])
            logging.debug("Cleared {}.".format(self.paths["temp"]))

    def rebuild_captures(self):
        self.images = build_captures_from_exif(self.paths["default"])

    def update_settings(self, config: dict):
        """Update settings from a config dictionary"""
        with self.lock:
            # Apply valid config params to camera object
            for key, value in config.items():  # For each provided setting
                if hasattr(self, key):  # If the instance has a matching property
                    setattr(self, key, value)  # Set to the target value

    def read_settings(self) -> dict:
        """Return the current settings as a dictionary"""
        return {"paths": self.paths}

    # RETURNING CAPTURES

    @property
    def image(self):
        """Return the latest captured image."""
        return last_entry(self.images.values())

    @property
    def video(self):
        """Return the latest recorded video."""
        return last_entry(self.videos.values())

    def image_from_id(self, image_id):
        """Return an image StreamObject with a matching ID."""
        logging.warning("image_from_id is deprecated. Access captures as a dictionary.")
        return entry_by_uuid(image_id, self.images.values())

    def video_from_id(self, video_id):
        """Return a video StreamObject with a matching ID."""
        logging.warning("video_from_id is deprecated. Access captures as a dictionary.")
        return entry_by_uuid(video_id, self.videos.values())

    # CREATING NEW CAPTURES

    def new_image(
        self,
        temporary: bool = True,
        filename: str = None,
        folder: str = "",
        fmt: str = "jpeg",
    ):

        """
        Create a new image capture object.

        Args:
            temporary (bool): Should the data be deleted after session ends. 
                Creating the capture with a content manager sets this to true.
            filename (str): Name of the stored file. Defaults to timestamp.
            folder (str): Name of the folder in which to store the capture.
            fmt (str): Format of the capture.
        """

        # Generate file name
        if not filename:
            filename = generate_numbered_basename(self.images.values())
            logging.debug(filename)
        filename = "{}.{}".format(filename, fmt)

        # Generate folder
        base_folder = self.paths["temp"] if temporary else self.paths["default"]
        folder = os.path.join(base_folder, folder)

        # Generate file path
        filepath = os.path.join(folder, filename)

        # Create capture object
        output = CaptureObject(filepath=filepath)
        # Insert a temporary tag if temporary
        if temporary:
            output.put_tags(["temporary"])

        # Update capture list
        capture_key = str(output.id)
        logging.debug(f"Adding image {output} with key {capture_key}")
        self.images[capture_key] = output

        return output

    def new_video(
        self,
        temporary: bool = False,
        filename: str = None,
        folder: str = "",
        fmt: str = "h264",
    ):

        """
        Create a new video capture object.

        Args:
            temporary (bool): Should the data be deleted after session ends. 
                Creating the capture with a content manager sets this to true.
            filename (str): Name of the stored file. Defaults to timestamp.
            folder (str): Name of the folder in which to store the capture.
            fmt (str): Format of the capture.
        """
        # TODO: Remove the redundancy here

        # Generate file name
        if not filename:
            filename = generate_numbered_basename(self.videos.values())
            logging.debug(filename)
        filename = "{}.{}".format(filename, fmt)

        # Generate folder
        base_folder = self.paths["temp"] if temporary else self.paths["default"]
        folder = os.path.join(base_folder, folder)

        # Generate file path
        filepath = os.path.join(folder, filename)

        # Create capture object
        output = CaptureObject(filepath=filepath)
        # Insert a temporary tag if temporary
        if temporary:
            output.put_tags(["temporary"])

        # Update capture list
        capture_key = str(output.id)
        logging.debug(f"Adding video {output} with key {capture_key}")
        self.videos[capture_key] = output

        return output
