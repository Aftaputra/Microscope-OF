# -*- coding: utf-8 -*-
"""
Defines a microscope object, binding a camera and stage with basic functionality.
"""
import logging
import pkg_resources
import uuid
from typing import Tuple
from expiringdict import ExpiringDict

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

from openflexure_microscope.utilities import serialise_array_b64, Timer
from openflexure_microscope.config import user_settings, user_configuration

from labthings import CompositeLock


class Microscope:
    """
    A basic microscope object.

    The camera and stage objects may already be initialised, and can be passed as arguments.
    """

    def __init__(self, settings=user_settings, configuration=user_configuration):
        self.id = f"openflexure:microscope:{uuid.uuid4()}"
        self.name = self.id

        self.captures = CaptureManager()

        self.fov = [0, 0]  #: Microscope field-of-view in stage motor steps

        # Store settings and configuration files
        self.settings_file = settings
        self.configuration_file = configuration

        self.extension_settings = {}

        # Initialise with an empty composite lock
        #: :py:class:`labthings.CompositeLock`: Composite lock for locking both camera and stage
        self.lock = CompositeLock([])

        self.camera = None  #: Currently connected camera object
        self.stage = None  #: Currently connected stage object

        self.setup(self.configuration_file.load())  # Attach components

        # Apply settings loaded from file
        self.update_settings(self.settings_file.load())

        # Data cache
        self.configuration_cache = ExpiringDict(max_len=100, max_age_seconds=3600)
        self.metadata_cache = ExpiringDict(max_len=100, max_age_seconds=3600)

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
        with self.lock:
            state = {"camera": self.camera.state, "stage": self.stage.state}
            return state

    def update_settings(self, settings: dict):
        """
        Applies a settings dictionary to the microscope. Missing parameters will be left untouched.
        """
        with self.lock:
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

        with self.lock:
            # If attached to a camera
            if self.camera:
                    settings_current_camera = self.camera.read_settings()
                    settings_current["camera"] = settings_current_camera

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

    def force_get_configuration(self):
        with self.lock:
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

    def get_configuration(self, cache_key=None):
        if cache_key:
            cached_config = self.configuration_cache.get(cache_key, None)
            if cached_config:
                return cached_config
            else:
                full_config = self.force_get_configuration()
                self.configuration_cache[cache_key] = full_config
                return full_config
        return self.force_get_configuration()

    @property
    def configuration(self):
        return self.get_configuration()

    def force_get_metadata(self):
        """
        Read cachable bits of microscope metadata.
        Currently ID, settings, and configuration can be cached
        """
        system_metadata = {
            "id": self.id,
            "settings": self.read_settings(full=False),
            "configuration": self.get_configuration(),
        }

        return system_metadata

    def get_metadata(self, cache_key=None):
        """
        Read microscope metadata, with partial caching
        """
        metadata = {}

        # Load cached bits of metadata
        if cache_key:
            logging.debug(f"Reading cached microscope metadata: {cache_key}")
            metadata = self.metadata_cache.get(cache_key, None)
            if not metadata:
                logging.debug(f"Building and caching microscope metadata: {cache_key}")
                metadata = self.force_get_metadata()
                self.metadata_cache[cache_key] = metadata
        else:
            logging.debug(f"Building microscope metadata: {cache_key}")
            metadata = self.force_get_metadata()
        
        # Keys that should never be cached
        metadata.update({
            "state": self.state,
        })

        return metadata

    @property
    def metadata(self):
        return self.get_metadata()

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
        cache_key: str = None
    ):
        logging.debug(f"Microscope capturing to {filename}")
        if not annotations:
            annotations = {}
        if not metadata:
            metadata = {}
        if not tags:
            tags = []

        # Read metadata for capture
        full_metadata = {"instrument": self.get_metadata(cache_key), **metadata}

        # Do capture
        with self.camera.lock:
            # Create output object
            output = self.captures.new_image(
                temporary=temporary, filename=filename, folder=folder, fmt=fmt
            )

            # Capture to output object
            logging.info(f"Starting microscope capture {output.file}")
            print(output)
            self.camera.capture(
                output,
                use_video_port=use_video_port,
                resize=resize,
                bayer=bayer,
                fmt=fmt,
            )

        output.put_and_save(tags, annotations, full_metadata)
        logging.debug(f"Finished capture to {output.file}")

        return output
