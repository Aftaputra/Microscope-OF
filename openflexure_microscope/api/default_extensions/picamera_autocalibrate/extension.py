import logging
from contextlib import contextmanager

import labthings.fields as fields
from flask import abort
from labthings import find_component
from labthings.extensions import BaseExtension
from labthings.views import ActionView

from openflexure_microscope.camera.base import BaseCamera
from openflexure_microscope.microscope import Microscope

from .recalibrate_utils import (
    adjust_shutter_and_gain_from_raw,
    adjust_white_balance_from_raw,
    flat_lens_shading_table,
    get_channel_percentiles,
    lst_from_camera,
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
        self.add_view(
            GetRawChannelPercentilesView,
            "/get_raw_channel_percentiles",
            endpoint="get_raw_channel_percentiles",
        )
        self.add_view(
            AutoExposureFromRawView,
            "/auto_exposure_from_raw",
            endpoint="auto_exposure_from_raw",
        )
        self.add_view(
            AutoWhiteBalanceFromRawView,
            "/auto_white_balance_from_raw",
            endpoint="auto_white_balance_from_raw",
        )


def find_microscope() -> Microscope:
    """Locate the microscope and raise a sensible error if it's missing."""
    microscope = find_component("org.openflexure.microscope")

    if not microscope:
        abort(
            503, "No microscope connected. Unable to use camera calibration functions."
        )

    if not hasattr(microscope.camera, "picamera"):
        abort(503, "The PiCamera calibration plugin requires a Raspberry Pi camera.")

    return microscope


class RecalibrateView(ActionView):
    args = {
        "skip_auto_exposure": fields.Bool(
            missing=False,
            description=(
                "By default we perform an auto-exposure and AWB "
                "step before updating the lens shading table.  Set "
                "this argument to True to disable those steps."
            ),
        )
    }

    def post(self, args):
        """Reset the camera's settings.

        This generates new gains, exposure time, and lens shading
        table such that the background is as uniform as possible
        with a gray level of 230.  It takes a little while to run.
        """
        microscope = find_microscope()
        logging.info("Starting microscope recalibration...")
        picamera = microscope.camera.picamera
        with microscope.camera.lock:
            if not args.get("skip_auto_exposure"):
                adjust_shutter_and_gain_from_raw(picamera)
                adjust_white_balance_from_raw(picamera)
            lst = lst_from_camera(picamera)
            with pause_stream(microscope.camera) as scamera:
                scamera.picamera.lens_shading_table = lst
            microscope.save_settings()


class FlattenLSTView(ActionView):
    def post(self):
        microscope = find_microscope()
        with pause_stream(microscope.camera) as scamera:
            flat_lst = flat_lens_shading_table(scamera.camera)
            scamera.camera.lens_shading_table = flat_lst
        microscope.save_settings()


class DeleteLSTView(ActionView):
    def post(self):
        microscope = find_microscope()
        with pause_stream(microscope.camera) as scamera:
            scamera.camera.lens_shading_table = None
        microscope.save_settings()


class AutoExposureFromRawView(ActionView):
    args = {
        "target_white_level": fields.Int(
            missing=700,
            example=700,
            description=(
                "The pixel value (10-bit format) that we aim for when adjusting shutter/gain."
            ),
        ),
        "max_iterations": fields.Int(
            missing=20,
            description=(
                "The number of adjustments to the camera's settings to make before giving up."
            ),
        ),
        "tolerance": fields.Float(
            missing=0.05,
            example=0.05,
            description=(
                "We stop adjusting when we get within this fraction of the target "
                "value.  It is a number between 0 and 1, usually 0.01--0.1."
            ),
        ),
        "percentile": fields.Float(
            missing=99.9,
            example=99.9,
            description=(
                "A float between 0 and 100 setting the centile to use "
                "to measure the white point of the image.  A value "
                "of 99.9 allows 0.1% of the pixels to be erroneously "
                "bright - this helps stability in low light."
            ),
        ),
    }

    def post(self, args):
        camera = find_component("org.openflexure.microscope").camera

        with camera.lock:
            adjust_shutter_and_gain_from_raw(
                camera.picamera, **args  # I'm relying on the schema to fill in missing values
            )


class AutoWhiteBalanceFromRawView(ActionView):
    args = {
        "percentile": fields.Float(
            missing=99.9,
            example=99.9,
            description=(
                "A float between 0 and 100 setting the centile to use "
                "to measure the white point of the image.  A value "
                "of 99.9 allows 0.1% of the pixels to be erroneously "
                "bright - this helps stability in low light."
            ),
        )
    }

    def post(self, args):
        camera = find_component("org.openflexure.microscope").camera.picamera
        adjust_white_balance_from_raw(
            camera, **args  # I'm relying on the schema to fill in missing values
        )


class GetRawChannelPercentilesView(ActionView):
    args = {
        "percentile": fields.Float(
            example=99.9,
            description="A float between 0 and 100 setting the centile to calculate",
        )
    }
    schema = fields.List(fields.Integer)

    def post(self, args):
        camera = find_component("org.openflexure.microscope").camera.picamera
        return get_channel_percentiles(camera, args["percentile"])
