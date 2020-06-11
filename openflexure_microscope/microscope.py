# -*- coding: utf-8 -*-
"""
Defines a microscope object, binding a camera and stage with basic functionality.
"""
import logging
import pkg_resources
import uuid
from typing import Tuple

import gevent

from openflexure_microscope.captures import CaptureManager

from openflexure_microscope.stage.mock import MissingStage
from openflexure_microscope.camera.mock import MissingCamera
from openflexure_microscope.stage.sanga import SangaStage

try:
    from openflexure_microscope.camera.pi import PiCameraStreamer
except Exception as e:
    logging.error(e)
    logging.warning("Unable to import PiCameraStreamer")
from openflexure_microscope.camera.mock import MissingCamera

from openflexure_microscope.utilities import serialise_array_b64
from openflexure_microscope.config import user_settings, user_configuration

from labthings.core.lock import CompositeLock


class Microscope:
    """
    A basic microscope object.

    The camera and stage objects may already be initialised, and can be passed as arguments.
    """

    def __init__(self, settings=user_settings, configuration=user_configuration):
        self.id = uuid.uuid4()
        self.name = self.id

        self.captures = CaptureManager()

        self.fov = [0, 0]  #: Microscope field-of-view in stage motor steps

        # Store settings and configuration files
        self.settings_file = settings
        self.configuration_file = configuration

        self.extension_settings = {}

        # Initialise with an empty composite lock
        #: :py:class:`labthings.lock.CompositeLock`: Composite lock for locking both camera and stage
        self.lock = CompositeLock([])

        self.camera = None  #: Currently connected camera object
        self.stage = None  #: Currently connected stage object

        self.setup(self.configuration_file.load())  # Attach components

        # Apply settings loaded from file
        self.update_settings(self.settings_file.load())

    def __enter__(self):
        """Create microscope on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close microscope on context exit."""
        self.close()

    def close(self):
        """Shut down the microscope hardware."""
        logging.info("Closing {}".format(self))
        if self.camera:
            try:
                self.camera.close()
            except TimeoutError as e:
                logging.error(e)
        if self.stage:
            try:
                self.stage.close()
            except TimeoutError as e:
                logging.error(e)
        self.captures.close()
        logging.info("Closed {}".format(self))

    def setup(self, configuration):
        """
        Attach microscope components based on initially passed configuration file
        """

        ### Detector
        logging.info("Creating camera")
        if configuration.get("camera"):
            camera_type = configuration["camera"].get("type")
            if camera_type in ("PiCamera", "PiCameraStreamer"):
                try:
                    self.camera = PiCameraStreamer()
                except Exception as e:
                    logging.error(e)
                    logging.warning("No compatible camera hardware found.")

        ### Stage
        logging.info("Creating stage")
        if configuration.get("stage"):
            stage_type = configuration["stage"].get("type")
            stage_port = configuration["stage"].get("port")
            if stage_type in ("SangaBoard", "SangaStage"):
                try:
                    self.stage = SangaStage(port=stage_port)
                except Exception as e:
                    logging.error(e)
                    logging.warning("No compatible Sangaboard hardware found.")

        logging.info("Handling fallbacks")
        ### Fallbacks
        if not self.camera:
            self.camera = MissingCamera()
        if not self.stage:
            self.stage = MissingStage()

        ### Locks
        logging.info("Creating locks")
        if hasattr(self.camera, "lock"):
            self.lock.locks.append(self.camera.lock)
        if hasattr(self.stage, "lock"):
            self.lock.locks.append(self.stage.lock)

    def has_real_stage(self) -> bool:
        """
        Check if a real (non-mock) stage is currently attached.
        """
        if hasattr(self, "stage") and not isinstance(self.stage, MissingStage):
            return True
        else:
            return False

    def has_real_camera(self):
        """
        Check if a real (non-mock) camera is currently attached.
        """
        if hasattr(self, "camera") and not isinstance(self.camera, MissingCamera):
            return True
        else:
            return False

    # Create unified state
    @property
    def state(self):
        """Dictionary of the basic microscope state.

        Return:
            dict: Dictionary containing complete microscope state
        """
        state = {"camera": self.camera.state, "stage": self.stage.state}
        return state

    def update_settings(self, settings: dict):
        """
        Applies a settings dictionary to the microscope. Missing parameters will be left untouched.
        """
        logging.debug("Microscope: Applying settings: {}".format(settings))

        # If attached to a camera
        if ("camera" in settings) and self.camera:
            self.camera.update_settings(settings.get("camera", {}))

        # If attached to a stage
        if ("stage" in settings) and self.stage:
            self.stage.update_settings(settings.get("stage", {}))

        # Capture manager
        self.captures.update_settings(settings.get("captures", {}))

        # Microscope settings
        if "id" in settings:
            self.id = settings["id"]
        if "name" in settings:
            self.name = settings["name"]
        if "fov" in settings:
            self.fov = settings["fov"]

        # Extension settings
        if "extensions" in settings:
            self.extension_settings.update(settings["extensions"])

        # TODO: warn if there are settings that we silently ignore

    def read_settings(self, full: bool = True):
        """
        Get an updated settings dictionary.

        Reads current attributes and properties from connected hardware,
        then merges those with the currently saved settings.

        This is to ensure that settings for currently disconnected hardware
        don't get removed from the settings file.
        """

        settings_current = {
            "id": self.id,
            "name": self.name,
            "fov": self.fov,
            "extensions": self.extension_settings,
        }

        # If attached to a camera
        if self.camera:
            settings_current_camera = self.camera.read_settings()
            settings_current["camera"] = settings_current_camera

            # Store an encoded copy of the PiCamera lens shading table, if it exists
            if hasattr(self.camera, "read_lens_shading_table"):
                # Read LST. Returns None if no LST is active
                lst_arr = self.camera.read_lens_shading_table()

                if lst_arr is not None:
                    b64_string, dtype, shape = serialise_array_b64(lst_arr)

                    settings_current["camera"]["lens_shading_table"] = {
                        "@type": "ndarray",
                        "b64_string": b64_string,
                        "dtype": dtype,
                        "shape": shape,
                    }

        # If attached to a stage
        if self.stage:
            settings_current_stage = self.stage.read_settings()
            settings_current["stage"] = settings_current_stage

        # Capture manager
        settings_current_captures = self.captures.read_settings()
        settings_current["captures"] = settings_current_captures

        settings_full = self.settings_file.merge(settings_current)

        if full:
            return settings_full
        else:
            return settings_current

    def save_settings(self):
        """
        Merges the current settings back to disk
        """
        # Read curent config
        current_config = self.read_settings()
        # Save config to file
        self.settings_file.save(current_config, backup=True)

    @property
    def configuration(self):
        initial_configuration = self.configuration_file.load()

        current_configuration = {
            "application": {
                "name": "openflexure-microscope-server",
                "version": pkg_resources.get_distribution(
                    "openflexure-microscope-server"
                ).version,
            },
            "stage": {
                "type": self.stage.__class__.__name__,
                **self.stage.configuration,
            },
            "camera": {
                "type": self.camera.__class__.__name__,
                **self.camera.configuration,
            },
        }

        initial_configuration.update(current_configuration)
        return initial_configuration

    @property
    def metadata(self):
        """
        Microscope system metadata, to be applied to basically all captures
        """
        system_metadata = {
            "id": self.id,
            "settings": self.read_settings(full=False),
            "state": self.state,
            "configuration": self.configuration,
        }

        return system_metadata

    def add_metadata_to_capture(output, metadata, annotations, tags):
        logging.debug(f"Waiting for {output.file}")
        # Wait for the file to be written to disk
        output.file_ready.wait()
        logging.info(f"Asynchronously injecting EXIF data into {output.file}")
        # Inject system metadata
        output.put_metadata({"instrument": self.metadata})
        # Insert custom metadata
        output.put_metadata(metadata)
        # Insert custom metadata
        output.put_annotations(annotations)
        # Insert custom tags
        output.put_tags(tags)
        logging.info(f"Finished injecting EXIF data into {output.file}")

    def capture(
        self,
        filename: str = None,
        folder: str = "",
        temporary: bool = False,
        use_video_port: bool = False,
        resize: Tuple[int, int] = None,
        bayer: bool = True,
        fmt: str = "jpeg",
        annotations: dict = None,
        tags: list = None,
        metadata: dict = None,
    ):
        logging.debug(f"Microscope capturing to {filename}")
        if not annotations:
            annotations = {}
        if not metadata:
            metadata = {}
        if not tags:
            tags = []

        with self.camera.lock:
            # Create output object
            output = self.captures.new_image(
                temporary=temporary, filename=filename, folder=folder, fmt=fmt
            )

            # Capture to output object
            logging.info("Starting microscope capture...")
            self.camera.capture(
                output,
                use_video_port=use_video_port,
                resize=resize,
                bayer=bayer,
                fmt=fmt,
            )

        # Gether metadata from hardware in a greenlet
        gevent.spawn(self.add_metadata_to_capture, output, metadata, annotations, tags)

        logging.info(f"Finished capture to {output.file}")

        return output
