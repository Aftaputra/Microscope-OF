from labthings.server.view import View
from labthings.server.find import find_component
from labthings.server.extensions import BaseExtension
from labthings.server.decorators import marshal_task, ThingAction

from labthings.core.tasks import taskify

from flask import abort

from contextlib import contextmanager
import logging

# Type hinting
from typing import Tuple

from .recalibrate_utils import recalibrate_camera, auto_expose_and_freeze_settings, flat_lens_shading_table

@contextmanager
def pause_stream(scamera, resolution: Tuple[int, int] = None):
    """This context manager locks a streaming camera, and pauses the stream.

    The stream is re-enabled, with the original resolution, once the with
    block has finished.
    """
    with scamera.lock:
        assert not scamera.record_active, "We can't pause the camera's video stream while a recording is in progress."
        streaming = scamera.stream_active
        old_resolution = scamera.camera.resolution
        if streaming:
            logging.info("Stopping stream in pause_stream context manager")
            scamera.stop_stream_recording(resolution=resolution)
        try:
            yield scamera
        finally:
            scamera.camera.resolution = old_resolution
            if streaming:
                logging.info("Restarting stream in pause_stream context manager")
                scamera.start_stream_recording()

def recalibrate(microscope):
    """Reset the camera's settings.

    This generates new gains, exposure time, and lens shading
    table such that the background is as uniform as possible
    with a gray level of 230.  It takes a little while to run.
    """
    with pause_stream(microscope.camera) as scamera:
        auto_expose_and_freeze_settings(scamera.camera) # scamera.camera is the PiCamera object
        recalibrate_camera(scamera.camera)
    microscope.save_settings()


@ThingAction
class RecalibrateView(View):
    @marshal_task
    def post(self):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to recalibrate.")

        logging.info("Starting microscope recalibration...")

        return taskify(recalibrate)(microscope)

@ThingAction
class FlattenLSTView(View):
    def post(self):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to flatten the lens shading table.")

        try:
            with pause_stream(microscope.camera) as scamera:
                flat_lst = flat_lens_shading_table(scamera.camera)
                scamera.camera.lens_shading_table = flat_lst
            microscope.save_settings()
        except:
            logging.exception("Error flattening the lens shading table.")
            abort(503, "Couldn't flatten the lens shading table - do you have the forked PiCamera library installed?")

@ThingAction
class DeleteLSTView(View):
    def post(self):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to flatten the lens shading table.")

        try:
            with pause_stream(microscope.camera) as scamera:
                scamera.camera.lens_shading_table = None
            microscope.save_settings()
        except:
            logging.exception("Error deleting the lens shading table.")
            abort(503, "Couldn't flatten the lens shading table - do you have the forked PiCamera library installed?")


lst_extension_v2 = BaseExtension(
    "org.openflexure.calibration.picamera", version="2.0.0-beta.1", description="Routines to perform flat-field correction on the camera."
)

lst_extension_v2.add_method(
    recalibrate, "org.openflexure.calibration.picamera.recalibrate"
)

lst_extension_v2.add_view(RecalibrateView, "/recalibrate")
lst_extension_v2.add_view(FlattenLSTView, "/flatten_lens_shading_table")
lst_extension_v2.add_view(DeleteLSTView, "/delete_lens_shading_table")
