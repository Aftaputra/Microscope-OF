"""
API extension for stage calibration

This file contains the HTTP API for camera/stage calibration.
"""
from labthings.server.view import View
from labthings.server.find import find_component
from labthings.server.extensions import BaseExtension
from labthings.server.decorators import (
    marshal_task,
    ThingAction,
    use_args,
    ThingProperty,
)
from labthings.server import fields

from labthings.core.tasks import taskify
from labthings.core.utilities import get_by_path, set_by_path, create_from_path


from flask import abort, send_file

import logging
import time
import numpy as np
import PIL
import io
import os
import json

from .camera_stage_calibration_1d import (
    calibrate_backlash_1d,
    image_to_stage_displacement_from_1d,
)
from .camera_stage_tracker import Tracker

from openflexure_microscope.utilities import axes_to_array
from openflexure_microscope.paths import data_file_path
from openflexure_microscope.config import JSONEncoder

CSM_DATAFILE_NAME = "csm_calibration.json"
CSM_DATAFILE_PATH = data_file_path(CSM_DATAFILE_NAME)


class CSMExtension(BaseExtension):
    """
    Use the camera as an encoder, so we can relate camera and stage coordinates
    """

    def __init__(self):
        BaseExtension.__init__(
            self, "org.openflexure.camera_stage_mapping", version="0.0.1"
        )

    _microscope = None

    @property
    def microscope(self):
        # TODO: does caching the microscope actually help?
        if self._microscope is None:
            self._microscope = find_component("org.openflexure.microscope")
        return self._microscope

    def update_settings(self, settings):
        """Update the stored extension settings dictionary"""
        keys = ["extensions", self.name]
        dictionary = create_from_path(keys)
        set_by_path(dictionary, keys, settings)
        logging.info(f"Updating settings with {dictionary}")
        self.microscope.update_settings(dictionary)
        self.microscope.save_settings()

    def get_settings(self):
        """Retrieve the settings for this extension"""
        keys = ["extensions", self.name]
        return get_by_path(self.microscope.read_settings(), keys)

    def camera_stage_functions(self):
        """Return functions that allow us to interface with the microscope"""
        self.microscope.camera.start_worker()  # ensure the worker thread is running, so there is an MJPEG stream

        def grab_image():
            jpeg = self.microscope.camera.get_frame()
            return np.array(PIL.Image.open(io.BytesIO(jpeg)))

        def get_position():
            return self.microscope.stage.position

        move = self.microscope.stage.move_abs

        return grab_image, get_position, move

    def calibrate_1d(self, direction):
        """Move a microscope's stage in 1D, and figure out the relationship with the camera"""
        grab_image, get_position, move = self.camera_stage_functions()

        def wait():
            time.sleep(0.2)

        tracker = Tracker(grab_image, get_position, settle=wait)

        return calibrate_backlash_1d(tracker, move, direction)

    def calibrate_xy(self):
        """Move the microscope's stage in X and Y, to calibrate its relationship to the camera"""
        logging.info("Calibrating X axis:")
        cal_x = self.calibrate_1d(np.array([1, 0, 0]))
        logging.info("Calibrating Y axis:")
        cal_y = self.calibrate_1d(np.array([0, 1, 0]))

        # Combine X and Y calibrations to make a 2D calibration
        cal_xy = image_to_stage_displacement_from_1d([cal_x, cal_y])
        self.update_settings(cal_xy)

        data = {
            "camera_stage_mapping_calibration": cal_xy,
            "linear_calibration_x": cal_x,
            "linear_calibration_y": cal_y,
        }

        with open(CSM_DATAFILE_PATH, "w") as f:
            json.dump(data, f, cls=JSONEncoder)

        return data

    @property
    def image_to_stage_displacement_matrix(self):
        try:
            settings = self.get_settings()
            return settings["image_to_stage_displacement"]
        except KeyError:
            raise ValueError("The microscope has not yet been calibrated.")

    def move_in_image_coordinates(self, displacement_in_pixels):
        """Move by a given number of pixels on the camera"""
        p = np.array(displacement_in_pixels)
        relative_move = np.dot(p, self.image_to_stage_displacement_matrix)
        self.microscope.stage.move_rel([relative_move[0], relative_move[1], 0])


csm_extension = CSMExtension()


@ThingAction
class Calibrate1DView(View):
    @use_args(
        {"direction": fields.List(fields.Float(), required=True, example=[1, 0, 0])}
    )
    @marshal_task
    def post(self, args):
        """Calibrate one axis of the microscope stage against the camera."""

        direction = np.array(args.get("direction"))

        task = taskify(csm_extension.calibrate_1d)(direction)

        return task


csm_extension.add_view(Calibrate1DView, "/calibrate_1d", endpoint="calibrate_1d")


@ThingAction
class CalibrateXYView(View):
    @marshal_task
    def post(self):
        """Calibrate both axes of the microscope stage against the camera."""
        task = taskify(csm_extension.calibrate_xy)()

        return task


csm_extension.add_view(CalibrateXYView, "/calibrate_xy", endpoint="calibrate_xy")


@ThingAction
class MoveInImageCoordinatesView(View):
    @use_args(
        {
            "x": fields.Float(
                description="The number of pixels to move in X",
                required=True,
                example=100,
            ),
            "y": fields.Float(
                description="The number of pixels to move in Y",
                required=True,
                example=100,
            ),
        }
    )
    def post(self, args):
        logging.debug("moving in pixels")
        """Move the microscope stage, such that we move by a given number of pixels on the camera"""
        csm_extension.move_in_image_coordinates(
            np.array([args.get("x"), args.get("y")])
        )

        return csm_extension.microscope.state["stage"]["position"]


csm_extension.add_view(MoveInImageCoordinatesView, "/move_in_image_coordinates", endpoint="move_in_image_coordinates")


@ThingProperty
class GetCalibrationFile(View):
    def get(self):
        """Get the calibration data in JSON format."""
        datafile_name = CSM_DATAFILE_NAME
        datafile_path = CSM_DATAFILE_PATH

        if os.path.isfile(datafile_path):
            with open(datafile_path, "rb") as f:
                return json.load(f)
        else:
            return {}


csm_extension.add_view(GetCalibrationFile, "/get_calibration", endpoint="get_calibration")
