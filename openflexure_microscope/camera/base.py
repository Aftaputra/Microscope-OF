# -*- coding: utf-8 -*-
import logging
import threading
import time
import io
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
        self.frames = []
        self.last = None

        self.tracking = False

    def start_tracking(self):
        if not self.tracking:
            logging.info("Started tracking frame data")
            self.tracking = True

    def stop_tracking(self):
        if self.tracking:
            logging.info("Stopped tracking frame data")
            self.tracking = False

    def reset_tracking(self):
        self.frames = []

    def write(self, s):
        if self.tracking:
            frame = TrackerFrame(size=len(s), time=time.time())
            self.frames.append(frame)
            self.last = frame
        io.BytesIO.write(self, s)


class BaseCamera(metaclass=ABCMeta):
    """
    Base implementation of StreamingCamera.
    """

    def __init__(self):
        self.thread = None
        self.camera = None

        self.lock = StrictLock(name="Camera", timeout=None)

        self.stream = FrameStream()
        self.frames_iterator = None
        self.frame = None
        self.last_access = 0
        self.event = ClientEvent()
        self.stop = False  # Used to indicate that the stream loop should break

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
        logging.info("Closing {}".format(self))
        # Stop worker thread
        self.stop_worker()
        logging.info("Closed {}".format(self))

    # START AND STOP WORKER THREAD

    def start_worker(self, timeout: int = 5) -> bool:
        """Start the background camera thread if it isn't running yet."""
        timeout_time = time.time() + timeout

        self.last_access = time.time()
        self.stop = False

        if not self.stream_active:
            # Start background frame thread
            self.thread = threading.Thread(target=self._thread)
            self.thread.daemon = True
            self.thread.start()

            # wait until frames are available
            logging.info("Waiting for frames")
            while self.get_frame() is None:
                if time.time() > timeout_time:
                    raise TimeoutError("Timeout waiting for frames.")
                else:
                    time.sleep(0.1)
        return True

    def stop_worker(self, timeout: int = 5) -> bool:
        """Flag worker thread for stop. Waits for thread close or timeout."""
        logging.debug("Stopping worker thread")
        timeout_time = time.time() + timeout

        if self.stream_active:
            self.stop = True
            self.thread.join()  # Wait for stream thread to exit
            logging.debug("Waiting for stream thread to exit.")

        while self.stream_active:
            if time.time() > timeout_time:
                logging.debug("Timeout waiting for worker thread close.")
                raise TimeoutError("Timeout waiting for worker thread close.")
            else:
                time.sleep(0.1)
        return True

    # HANDLE STREAM FRAMES

    def get_frame(self):
        """Return the current camera frame."""
        self.last_access = time.time()

        # wait for a signal from the camera thread
        self.event.wait()
        self.event.clear()

        return self.frame

    @abstractmethod
    def frames(self):
        """Create generator that returns frames from the camera."""

    # WORKER THREAD

    def _thread(self):
        """Camera background thread."""
        self.frames_iterator = self.frames()
        logging.debug("Entering worker thread.")

        self.stream_active = True

        for frame in self.frames_iterator:
            self.frame = frame
            self.event.set()  # send signal to clients

            try:
                if self.stop is True:
                    logging.debug("Worker thread flagged for stop.")
                    self.frames_iterator.close()
                    break

            except AttributeError:
                pass

        logging.debug("BaseCamera worker thread exiting...")
        # Set stream_activate state
        self.stream_active = False
