"""OpenFlexure Microscope OpenCV Camera

This module defines a Thing that is responsible for using the stage and
camera together to perform an autofocus routine.

See repository root for licensing information.
"""
from __future__ import annotations
import io
import json
import logging
from typing import Literal, Optional
from threading import Thread

import cv2
import piexif

from labthings_fastapi.thing import Thing
from labthings_fastapi.utilities import get_blocking_portal
from labthings_fastapi.decorators import thing_action, thing_property
from labthings_fastapi.dependencies.metadata import GetThingStates
from labthings_fastapi.dependencies.blocking_portal import BlockingPortal
from labthings_fastapi.outputs.mjpeg_stream import MJPEGStreamDescriptor
from labthings_fastapi.outputs.blob import BlobOutput
from labthings_fastapi.types.numpy import NDArray


class JPEGBlob(BlobOutput):
    media_type = "image/jpeg"


class OpenCVCamera(Thing):
    """A Thing representing an OpenCV camera"""
    def __init__(self, camera_index: int=0):
        self.camera_index = camera_index
        self._capture_thread: Optional[Thread] = None
        self._capture_enabled = False

    def __enter__(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        self._capture_enabled = True
        self._capture_thread = Thread(target=self._capture_frames)
        self._capture_thread.start()
        return self
    
    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.cap.release()

    @thing_property
    def stream_active(self) -> bool:
        "Whether the MJPEG stream is active"
        if self._capture_enabled and self._capture_thread:
            return self._capture_thread.is_alive()
        return False
    mjpeg_stream = MJPEGStreamDescriptor()
    lores_mjpeg_stream = MJPEGStreamDescriptor()

    def _capture_frames(self):
        portal = get_blocking_portal(self)
        while self._capture_enabled:
            ret, frame = self.cap.read()
            if not ret:
                logging.error(f"Failed to capture frame from camera {self.camera_index}")
                break
            jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
            self.mjpeg_stream.add_frame(jpeg, portal)
            jpeg_lores = cv2.imencode(".jpg", cv2.resize(frame, (320, 240)))[1].tobytes()
            self.lores_mjpeg_stream.add_frame(jpeg_lores, portal)

    @thing_action
    def snap_image(self) -> NDArray:
        """Acquire one image from the camera.

        This action cannot run if the camera is in use by a background thread, for
        example if a preview stream is running.
        """
        return self.capture_array()

    @thing_action
    def capture_array(self) -> NDArray:
        """Acquire one image from the camera and return as an array

        This function will produce a nested list containing an uncompressed RGB image.
        It's likely to be highly inefficient - raw and/or uncompressed captures using
        binary image formats will be added in due course.
        """
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError(f"Failed to capture frame from camera {self.camera_index}")
        return frame
    
    @thing_action
    def capture_jpeg(
        self,
        metadata_getter: GetThingStates,
    ) -> JPEGBlob:
        """Acquire one image from the camera and return as a JPEG blob

        This function will produce a JPEG image.
        """
        frame = self.capture_array()
        jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.UserComment: json.dumps(metadata_getter()).encode("utf-8")
            },
            "GPS": {},
            "Interop": {},
            "1st": {},
            "thumbnail": None,
        }
        output = io.BytesIO()
        piexif.insert(piexif.dump(exif_dict), jpeg, output)
        return JPEGBlob.from_bytes(output.getvalue())

    @thing_action
    def grab_jpeg(
        self,
        portal: BlockingPortal,
        stream_name: Literal["main", "lores"] = "main",
    ) -> JPEGBlob:
        """Acquire one image from the preview stream and return as an array

        This differs from `capture_jpeg` in that it does not pause the MJPEG
        preview stream. Instead, we simply return the next frame from that
        stream (either "main" for the preview stream, or "lores" for the low
        resolution preview). No metadata is returned.
        """
        logging.info(f"StreamingPiCamera2.grab_jpeg(stream_name={stream_name}) starting")
        stream = (
            self.lores_mjpeg_stream if stream_name == "lores" else self.mjpeg_stream
        )
        frame = portal.call(stream.grab_frame)
        logging.info(f"StreamingPiCamera2.grab_jpeg(stream_name={stream_name}) got frame")
        return JPEGBlob.from_bytes(frame)

    @thing_action
    def grab_jpeg_size(
        self,
        portal: BlockingPortal,
        stream_name: Literal["main", "lores"] = "main",
    ) -> int:
        """Acquire one image from the preview stream and return its size"""
        stream = (
            self.lores_mjpeg_stream if stream_name == "lores" else self.mjpeg_stream
        )
        return portal.call(stream.next_frame_size)
