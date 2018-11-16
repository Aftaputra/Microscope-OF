# -*- coding: utf-8 -*-
import time
import io
import threading
from PIL import Image
import logging

try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident

from .capture import StreamObject


def last_entry(object_list: list):
    """Return the last entry of a list, if the list contains items."""
    if object_list:  # If any images have been captured
        return object_list[-1]  # Return the latest captured image
    else:
        return None


def entry_by_id(id: str, object_list: list):
    """Return an object from a list, if <object>.id matches id argument."""
    found = None
    for o in object_list:
        if o.id == id:
            found = o
    return found


class CameraEvent(object):
    """
    A frame-signaller object used by any instances or subclasses of BaseCamera.

    An event-like class that signals all active clients when a new frame is available.
    """
    def __init__(self):
        self.events = {}

    def wait(self, timeout: int=5):
        """Wait for the next frame (invoked from each client's thread)."""
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait(timeout)

    def set(self):
        """Signal that a new frame is available."""
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                if now - event[1] > 5:
                    remove = ident
        if remove:
            del self.events[remove]

    def clear(self):
        """Clear frame event, once processed."""
        self.events[get_ident()][0].clear()


class BaseCamera(object):
    """
    Base implementation of StreamingCamera.
    """
    def __init__(self):
        self.thread = None  #: Background thread reading frames from camera
        self.camera = None  #: Camera object

        self.frame = None  #: bytes: Current frame is stored here by background thread
        self.last_access = 0  #: time: Time of last client access to the camera
        self.event = CameraEvent()

        self.state = {}  #: dict: Dictionary for capture state
        self.settings = {}  #: dict: Dictionary of camera settings

        # Capture data
        self.images = []  #: list: List of image capture objects
        self.videos = []  #: list: List of video recording objects

    def __enter__(self):
        """Create camera on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close camera stream on context exit."""
        self.close()

    def close(self):
        """Close the BaseCamera and all attached StreamObjects."""
        # Close all StreamObjects
        for capture_list in [self.images, self.videos]:
            for stream_object in capture_list:
                stream_object.close()
        # Stop worker thread
        self.stop_worker()

    def wait_for_camera(self, timeout=5):
        """Wait for camera object, with 5 second timeout."""
        timeout_time = time.time() + timeout
        while not self.camera:
            if time.time() > timeout_time:
                raise TimeoutError("Timeout waiting for camera")
            else:
                pass

    # START AND STOP WORKER THREAD

    def start_worker(self, timeout: int=5) -> bool:
        """Start the background camera thread if it isn't running yet."""
        timeout_time = time.time() + timeout

        self.last_access = time.time()
        self.stop = False

        if self.thread is None:
            # start background frame thread
            self.thread = threading.Thread(target=self._thread)
            self.thread.start()

            # wait until frames are available
            logging.info("Waiting for frames")
            while self.get_frame() is None:
                if time.time() > timeout_time:
                    raise TimeoutError("Timeout waiting for frames.")
                else:
                    time.sleep(0)
        return True

    def stop_worker(self, timeout: int=5) -> bool:
        """Flag worker thread for stop. Waits for thread close or timeout."""
        logging.debug("Stopping worker thread")
        timeout_time = time.time() + timeout

        self.stop = True
        while self.thread:
            if time.time() > timeout_time:
                raise TimeoutError("Timeout waiting for worker thread close.")
            else:
                time.sleep(0)
        return True

    # HANDLE STREAM FRAMES

    def get_frame(self):
        """Return the current camera frame."""
        self.last_access = time.time()

        # wait for a signal from the camera thread
        self.event.wait()
        self.event.clear()

        return self.frame

    def frames(self):
        """Create generator that returns frames from the camera."""
        raise RuntimeError('Must be implemented by subclasses.')

    # RETURNING CAPTURES

    @property
    def image(self):
        """Return the latest captured image."""
        return last_entry(self.images)

    @property
    def video(self):
        """Return the latest recorded video."""
        return last_entry(self.videos)

    def image_from_id(self, id):
        """Return an image StreamObject with a matching ID."""
        return entry_by_id(id, self.images)

    def video_from_id(self, id):
        """Return a video StreamObject with a matching ID."""
        return entry_by_id(id, self.videos)

    # CREATING NEW CAPTURES

    def new_stream_object(
            self,
            stream_object,
            target_list: list,
            shunt_others: bool=True):
        """Add a new capture to a list of captures, and shunt all others."""
        if shunt_others:  # If shunting all older captures
            for obj in target_list:  # For each older capture
                obj.shunt()  # Shunt capture from memory to storage
        target_list.append(stream_object)
        return stream_object

    def new_image(self, stream_object, shunt_others=True):
        """Add a new capture to the image list, and shunt all others."""
        return self.new_stream_object(
            stream_object,
            self.images,
            shunt_others=shunt_others)

    def new_video(self, stream_object, shunt_others=True):
        """Add a new capture to the video list, and shunt all others."""
        return self.new_stream_object(
            stream_object,
            self.videos,
            shunt_others=shunt_others)

    # WORKER THREAD

    def _thread(self):
        """Camera background thread."""
        self.frames_iterator = self.frames()
        logging.debug("Entering worker thread.")

        for frame in self.frames_iterator:
            self.frame = frame
            self.event.set()  # send signal to clients
            time.sleep(0)

            # if there hasn't been any clients asking for frames in
            # the last 10 seconds then stop the thread
            if time.time() - self.last_access > 20:
                self.frames_iterator.close()
                break

            try:
                if self.stop is True:
                    logging.debug("Worker thread flagged for stop.")
                    self.frames_iterator.close()
                    break

            except AttributeError:
                pass

        logging.debug("BaseCamera worker thread exiting...")
        # Reset thread
        self.thread = None
