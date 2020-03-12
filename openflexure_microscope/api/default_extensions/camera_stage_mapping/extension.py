"""
API extension for stage calibration

This file contains the HTTP API for camera/stage calibration.
"""
from labthings.server.view import View
from labthings.server.find import find_component
from labthings.server.extensions import BaseExtension
from labthings.server.decorators import marshal_task, ThingAction, use_args
from labthings.server import fields

from labthings.core.tasks import taskify
from labthings.core.utilities import get_by_path, set_by_path, create_from_path


from flask import abort

import logging
import time
import numpy as np
import PIL
import io

from .camera_stage_calibration_1d import calibrate_backlash_1d, image_to_stage_displacement_from_1d
from .camera_stage_tracker import Tracker

def update_extension_settings(microscope, settings):
    """Update the stored extension settings dictionary"""
    keys = ["extensions","org.openflexure.camera_stage_mapping"]
    dictionary = create_from_path(keys)
    set_by_path(dictionary, keys, settings)

    microscope.update_settings(dictionary)
    microscope.save_settings()

def get_extension_settings(microscope):
    """Retrieve the settings for this extension"""
    keys = ["extensions","org.openflexure.camera_stage_mapping"]
    return get_by_path(microscope.read_settings, keys)

def camera_stage_functions(microscope):
    """Return functions that allow us to interface with the microscope"""
    microscope.camera.start_worker() # ensure the worker thread is running, so there is an MJPEG stream
    
    def grab_image():
        jpeg = microscope.camera.get_frame()
        return np.array(PIL.Image.open(io.BytesIO(jpeg)))
    
    def get_position():
        return microscope.stage.position
    
    move = microscope.stage.move_abs

    return grab_image, get_position, move

def calibrate_1d(microscope, direction):
    """Move a microscope's stage in 1D, and figure out the relationship with the camera"""
    grab_image, get_position, move = camera_stage_functions(microscope)

    def wait():
        time.sleep(0.2)

    tracker = Tracker(grab_image, get_position, settle=wait)

    return calibrate_backlash_1d(tracker, move, direction)



@ThingAction
class Calibrate1DView(View):
    @use_args({
        "direction": fields.List(fields.Float(), required=True, example=[1,0,0])
    })
    @marshal_task
    def post(self, args):
        """Calibrate one axis of the microscope stage against the camera."""
        microscope = find_component("org.openflexure.microscope")
        
        direction = np.array(args.get("direction"))

        task = taskify(calibrate_1d)(microscope, direction)

        return task





csm_extension = BaseExtension("org.openflexure.camera_stage_mapping", version="0.0.1")

csm_extension.add_method(calibrate_1d, "calibrate_1d")
#csm_extension.add_method(calibrate_xy, "calibrate_xy")

csm_extension.add_view(Calibrate1DView, "/calibrate_1d")