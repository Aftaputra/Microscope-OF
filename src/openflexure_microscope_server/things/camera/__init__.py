"""OpenFlexure Microscope Camera

This module defines the interface for cameras. Any compatible Thing
should enabe the server to work.

See repository root for licensing information.
"""
from __future__ import annotations
import logging
from typing import Literal

from labthings_fastapi.thing import Thing
from labthings_fastapi.decorators import thing_action, thing_property
from labthings_fastapi.dependencies.metadata import GetThingStates
from labthings_fastapi.dependencies.blocking_portal import BlockingPortal
from labthings_fastapi.outputs.mjpeg_stream import MJPEGStreamDescriptor
from labthings_fastapi.outputs.blob import blob_type
from labthings_fastapi.types.numpy import NDArray


JPEGBlob = blob_type("image/jpeg")

class CameraMeta:
    def __subclasscheck__(cls, C):
        """Override Python's default behaviour and use duck typing"""
        print(f"Checking if {C} is a camera...")
        for action in ["snap_image", "capture_array", "capture_jpeg", "grab_jpeg", "grab_jpeg_size"]:
            a = getattr(C, action, None)
            if not callable(a):
                return False
        for prop in ["stream_active"]:
            if not hasattr(C, prop):
                return False
        for k in ["mjpeg_stream", "lores_mjpeg_stream"]:
            stream = getattr(C, k)
            if not isinstance(stream, MJPEGStreamDescriptor):
                return False
        return True

    def __instancecheck__(cls, I):
        return cls.__subclasscheck__(I)


class Camera(Thing):
    __metaclass__ = CameraMeta
    """A Thing representing a camera"""

    def __enter__(self):
        raise NotImplementedError("Subclasses must implement __enter__")
    
    def __exit__(self, _exc_type, _exc_value, _traceback):
        raise NotImplementedError("Subclasses must implement __exit__")

    @thing_property
    def stream_active(self) -> bool:
        "Whether the MJPEG stream is active"
        raise NotImplementedError("Subclasses must implement stream_active")
    mjpeg_stream = MJPEGStreamDescriptor()
    lores_mjpeg_stream = MJPEGStreamDescriptor()

    @thing_action
    def snap_image(self) -> NDArray:
        """Acquire one image from the camera.

        This action cannot run if the camera is in use by a background thread, for
        example if a preview stream is running.
        """
        return self.capture_array()

    @thing_action
    def capture_array(
        self,
        resolution: Literal["lores", "main", "full"] = "main",
    ) -> NDArray:
        """Acquire one image from the camera and return as an array

        This function will produce a nested list containing an uncompressed RGB image.
        It's likely to be highly inefficient - raw and/or uncompressed captures using
        binary image formats will be added in due course.
        """
        raise NotImplementedError("Subclasses must implement capture_array")
    
    @thing_action
    def capture_jpeg(
        self,
        metadata_getter: GetThingStates,
        resolution: Literal["lores", "main", "full"] = "main",
    ) -> JPEGBlob:
        """Acquire one image from the camera and return as a JPEG blob

        This function will produce a JPEG image.
        """
        raise NotImplementedError("Subclasses must implement capture_jpeg")

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

