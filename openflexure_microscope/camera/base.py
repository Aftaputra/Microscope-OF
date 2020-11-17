# -*- coding: utf-8 -*-
import io
import logging
import time
from abc import ABCMeta, abstractmethod
from collections import namedtuple

from labthings import ClientEvent, StrictLock

# Class to store a frames metadata
TrackerFrame = namedtuple("TrackerFrame", ["size", "time"])


class FrameStream(io.BytesIO):
    """
    A file-like object used to analyse MJPEG frames.

    Instead of analysing a load of real MJPEG frames 
    after they've been stored in a BytesIO stream,
    we tell the camera to write frames to this class instead.

    We then do analysis as the frames are written, and discard the heavier
    image data.
    """

    def __init__(self, *args, **kwargs):
        # Array of TrackerFrame objects
        io.BytesIO.__init__(self, *args, **kwargs)
        # Array of TrackerFramer objects
        self.frames = []
        # Last acquired TrackerFramer object
        self.last = None

        # Are we currently tracking frame sizes?
        self.tracking = False

        # Event to track if a new frame is available since the last getvalue() call
        # We use a ClientEvent so that each thread can call getvalue() independantly
        self.new_frame = ClientEvent()

    def start_tracking(self):
        if not self.tracking:
            logging.debug("Started tracking frame data")
            self.tracking = True

    def stop_tracking(self):
        if self.tracking:
            logging.debug("Stopped tracking frame data")
            self.tracking = False

    def reset_tracking(self):
        self.frames = []

    def write(self, s):
        """
        Write a new frame to the FrameStream. Does a few things:
        1. If tracking frame size, store the size in self.frames
        2. Rewind and truncate the stream (delete previous frame)
        3. Store the new frame image
        4. Set the new_frame event
        """
        if self.tracking:
            frame = TrackerFrame(size=len(s), time=time.time())
            self.frames.append(frame)
            self.last = frame
        # Reset the stream for the next frame
        super().seek(0)
        super().truncate()
        # Write the new frame
        super().write(s)
        # Set the new frame event
        self.new_frame.set()

    def getvalue(self) -> bytes:
        """
        Clear tne new_frame event and return frame data
        """
        self.new_frame.clear()
        return super().getvalue()

    def getframe(self) -> bytes:
        """Wait for a new frame to be available, then return it"""
        self.new_frame.wait()
        return self.getvalue()


class BaseCamera(metaclass=ABCMeta):
    """
    Base implementation of StreamingCamera.
    """

    def __init__(self):
        self.camera = None

        self.lock = StrictLock(name="Camera", timeout=None)

        self.stream = FrameStream()

        self.stream_active = False
        self.record_active = False
        self.preview_active = False

    @property
    @abstractmethod
    def configuration(self):
        """The current camera configuration."""

    @property
    @abstractmethod
    def state(self):
        """The current read-only camera state."""

    @property
    def settings(self):
        return self.read_settings()

    @abstractmethod
    def update_settings(self, config: dict):
        """Update settings from a config dictionary"""
        with self.lock(timeout=None):
            # Apply valid config params to camera object
            for key, value in config.items():  # For each provided setting
                if hasattr(self, key):  # If the instance has a matching property
                    setattr(self, key, value)  # Set to the target value

    @abstractmethod
    def read_settings(self) -> dict:
        """Return the current settings as a dictionary"""
        return {}

    def __enter__(self):
        """Create camera on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close camera stream on context exit."""
        self.close()

    def close(self):
        """Close the BaseCamera and all attached StreamObjects."""
        logging.info("Closed %s", (self))
