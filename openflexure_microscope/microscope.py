# -*- coding: utf-8 -*-
"""
Defines a microscope object, binding a camera and stage with basic functionality.
"""
import logging
import pkg_resources
import uuid

from openflexure_microscope.stage.base import BaseStage
from openflexure_microscope.stage.mock import MockStage
from openflexure_microscope.camera.base import BaseCamera
from openflexure_microscope.camera.mock import MockStreamer

from openflexure_microscope.utilities import serialise_array_b64
from openflexure_microscope.config import user_settings

from openflexure_microscope.common.labthings_core.lock import CompositeLock


class Microscope:
    """
    A basic microscope object.

    The camera and stage objects may already be initialised, and can be passed as arguments.
    """

    def __init__(self):
        # Initial attributes
        self.id = uuid.uuid4()  #: Microscope UUID
        self.name = self.id  #: Microscope name (modifiable)
        self.fov = [0, 0]   #: Microscope field-of-view in stage motor steps
        self.camera = None  #: Currently connected camera object
        self.stage = None  #: Currently connected stage object

        # Initialise with an empty composite lock
        #: :py:class:`openflexure_microscope.common.lock.CompositeLock`: Composite lock for locking both camera and stage
        self.lock = CompositeLock([])

        # Apply settings loaded from file
        self.apply_settings(user_settings.load())

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
            self.camera.close()
        if self.stage:
            self.stage.close()
        logging.info("Closed {}".format(self))

    def attach(self, camera: BaseCamera, stage: BaseStage):
        """
        Retroactively attaches a camera and stage to the microscope object.

        Allows the microscope to be created as a "dummy", with hardware communications
        opened at a later time.

        Args:
            camera (:py:class:`openflexure_microscope.camera.base.BaseCamera`): camera object
            stage (:py:class:`openflexure_microscope.stage.base.BaseStage`): stage object
        """

        settings_full = self.read_settings()

        logging.debug("Attaching camera...")
        self.camera = (
            camera
        )  #: :py:class:`openflexure_microscope.camera.base.BaseCamera`: Picamera object
        if not self.camera:
            logging.info("No camera attached.")
        else:
            logging.info("Attached camera {}".format(camera))

            if hasattr(self.camera, "lock"):  # If camera has a lock
                logging.info("Attaching {} to composite lock.".format(self.camera.lock))
                # Add the lock to the microscope composite lock
                self.lock.locks.append(self.camera.lock)

        logging.debug("Attaching stage...")
        self.stage = (
            stage
        )  #: :py:class:`openflexure_microscope.stage.base.BaseStage`: OpenFlexure stage object
        if not self.stage:
            logging.info("No stage attached.")
        else:
            logging.info("Attached stage {}".format(stage))

            if hasattr(self.stage, "lock"):  # If stage object has a lock
                logging.info(
                    "Attaching lock {} to composite lock.".format(self.stage.lock)
                )
                # Add the lock to the microscope composite lock
                self.lock.locks.append(self.stage.lock)

        logging.info("Reapplying settings to newly attached devices")
        self.apply_settings(settings_full)

    def has_real_stage(self) -> bool:
        """
        Check if a real (non-mock) stage is currently attached.
        """
        if hasattr(self, "stage") and not isinstance(self.stage, MockStage):
            return True
        else:
            return False

    def has_real_camera(self):
        """
        Check if a real (non-mock) camera is currently attached.
        """
        if hasattr(self, "camera") and not isinstance(self.camera, MockStreamer):
            return True
        else:
            return False

    # Create unified status
    @property
    def status(self):
        """Dictionary of the basic microscope status.

        Return:
            dict: Dictionary containing complete microscope status
        """
        state = {
            "camera": self.camera.status,
            "stage": self.stage.status,
            "version": pkg_resources.get_distribution("openflexure_microscope").version,
        }
        return state

    def apply_settings(self, config: dict):
        """
        Applies a settings dictionary to the microscope. Missing parameters will be left untouched.
        """
        logging.debug("Microscope: Applying config: {}".format(config))

        # If attached to a camera
        if ("camera_settings" in config) and self.camera:
            self.camera.apply_settings(config["camera_settings"])

        # If attached to a stage
        if ("stage_settings" in config) and self.stage:
            self.stage.apply_settings(config["stage_settings"])

        # Todo: tidy up with some loopy goodness
        if "id" in config:
            self.id = config["id"]
        if "name" in config:
            self.name = config["name"]
        if "fov" in config:
            self.fov = config["fov"]

    def read_settings(self, json_safe=False):
        """
        Get an updated settings dictionary.

        Reads current attributes and properties from connected hardware,
        then merges those with the currently saved settings.

        This is to ensure that settings for currently disconnected hardware
        don't get removed from the settings file.
        """

        settings_current = {"id": self.id, "name": self.name, "fov": self.fov}

        # If attached to a camera
        if self.camera:
            settings_current_camera = self.camera.read_settings()
            settings_current["camera_settings"] = settings_current_camera

        # If attached to a stage
        if self.stage:
            settings_current_stage = self.stage.read_settings()
            settings_current["stage_settings"] = settings_current_stage

        settings_full = user_settings.merge(settings_current)

        return settings_full

    def save_settings(self):
        """
        Merges the current settings back to disk
        """
        # Read curent config
        current_config = self.read_settings()
        # Save config to file
        if self.camera:
            self.camera.save_settings()
        if self.stage:
            self.stage.save_settings()
        user_settings.save(current_config, backup=True)

    @property
    def metadata(self):
        """
        Microscope system metadata, to be applied to basically all captures
        """
        system_metadata = {
            "microscope_settings": self.read_settings(),
            "microscope_state": self.status,
            "microscope_id": self.id,
            "microscope_name": self.name,
        }

        # Store an encoded copy of the PiCamera lens shading table, if it exists
        if self.camera and hasattr(self.camera, "read_lens_shading_table"):
            # Read LST. Returns None if no LST is active
            lst_arr = self.camera.read_lens_shading_table()

            b64_string, dtype, shape = serialise_array_b64(lst_arr)

            system_metadata["lens_shading_table"] = {
                "b64_string": b64_string,
                "dtype": dtype,
                "shape": shape,
            }

        return system_metadata
