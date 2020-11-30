import logging
from contextlib import contextmanager

import picamerax
from flask import abort
from labthings import find_component
from labthings.extensions import BaseExtension
from labthings.views import ActionView

from openflexure_microscope.camera.base import BaseCamera
from openflexure_microscope.microscope import Microscope

from .recalibrate_utils import (
    auto_expose_and_freeze_settings,
    flat_lens_shading_table,
    recalibrate_camera,
)


@contextmanager
def pause_stream(scamera: BaseCamera):
    """This context manager locks a streaming camera, and pauses the stream.

    The stream is re-enabled, with the original resolution, once the with
    block has finished.
    """
    with scamera.lock:
        assert (
            not scamera.record_active
        ), "We can't pause the camera's video stream while a recording is in progress."
        streaming = scamera.stream_active
        old_resolution = scamera.stream_resolution
        if streaming:
            logging.info("Stopping stream in pause_stream context manager")
            scamera.stop_stream()
        try:
            yield scamera
        finally:
            scamera.stream_resolution = old_resolution
            if streaming:
                logging.info("Restarting stream in pause_stream context manager")
                scamera.start_stream()


class LSTExtension(BaseExtension):
    def __init__(self) -> None:
        super().__init__(
            "org.openflexure.calibration.picamera",
            version="2.0.0-beta.1",
            description="Routines to perform flat-field correction on the camera.",
        )

        self.add_view(RecalibrateView, "/recalibrate", endpoint="recalibrate")
        self.add_view(
            FlattenLSTView,
            "/flatten_lens_shading_table",
            endpoint="flatten_lens_shading_table",
        )
        self.add_view(
            DeleteLSTView,
            "/delete_lens_shading_table",
            endpoint="delete_lens_shading_table",
        )

    def recalibrate(self, microscope: Microscope):
        """Reset the camera's settings.

        This generates new gains, exposure time, and lens shading
        table such that the background is as uniform as possible
        with a gray level of 230.  It takes a little while to run.
        """
        with pause_stream(microscope.camera) as scamera:
            if hasattr(scamera, "picamera"):
                picamera_obj: picamerax.PiCamera = getattr(scamera, "picamera")
                auto_expose_and_freeze_settings(picamera_obj)
                recalibrate_camera(picamera_obj)
                microscope.save_settings()
            else:
                raise RuntimeError(
                    "Recalibrate can only be used with a Raspberry Pi camera"
                )


class RecalibrateView(ActionView):
    def post(self):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(503, "No microscope connected. Unable to recalibrate.")

        logging.info("Starting microscope recalibration...")

        return self.extension.recalibrate(microscope)


class FlattenLSTView(ActionView):
    def post(self):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(
                503,
                "No microscope connected. Unable to flatten the lens shading table.",
            )

        with pause_stream(microscope.camera) as scamera:
            flat_lst = flat_lens_shading_table(scamera.camera)
            scamera.camera.lens_shading_table = flat_lst
        microscope.save_settings()


class DeleteLSTView(ActionView):
    def post(self):
        microscope = find_component("org.openflexure.microscope")

        if not microscope:
            abort(
                503,
                "No microscope connected. Unable to flatten the lens shading table.",
            )

        with pause_stream(microscope.camera) as scamera:
            scamera.camera.lens_shading_table = None
        microscope.save_settings()
