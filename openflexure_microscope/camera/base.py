# -*- coding: utf-8 -*-
import time
import io
import os
import threading
from PIL import Image
import datetime
import yaml
import logging

try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident

from .capture import CaptureObject, capture_from_dict, BASE_CAPTURE_PATH
from openflexure_microscope.config import USER_CONFIG_DIR
from openflexure_microscope.utilities import entry_by_id
from openflexure_microscope.lock import StrictLock


def last_entry(object_list: list):
    """Return the last entry of a list, if the list contains items."""
    if object_list:  # If any images have been captured
        return object_list[-1]  # Return the latest captured image
    else:
        return None


def generate_basename():
    """Return a default filename based on the capture datetime"""
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


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


def generate_basename(obj_list: list) -> str:
    initial_basename = generate_basename()
    basename = initial_basename
    # Handle clashing
    iterator = 1
    while basename in [obj.basename for obj in obj_list]:
        basename = initial_basename + "_{}".format(iterator)
        iterator += 1

    return basename


class BaseCamera(object):
    """
    Base implementation of StreamingCamera.
    """
    def __init__(self):
        self.thread = None  #: Background thread reading frames from camera
        self.camera = None  #: Camera object

        self.lock = StrictLock(timeout=1)  #: :py:class:`openflexure_microscope.lock.StrictLock`: Strict lock controlling thread access to camera hardware

        self.frame = None  #: bytes: Current frame is stored here by background thread
        self.last_access = 0  #: time: Time of last client access to the camera
        self.event = CameraEvent()

        self.stream_timeout = 20  #: int: Number of inactive seconds before timing out the stream
        self.stream_timeout_enabled = True  #: bool: Enable or disable timing out the stream

        self.state = {}  #: dict: Dictionary for capture state
        self.config = {}  #: dict: Dictionary of base camera config
        self.paths = {
            'image': BASE_CAPTURE_PATH,
            'video': BASE_CAPTURE_PATH,
        }  #: dict: Dictionary of capture paths

        # Capture data
        self.images = []  #: list: List of image capture objects
        self.videos = []  #: list: List of video recording objects

        # Capture data files
        self.images_db = os.path.join(USER_CONFIG_DIR, "images_db.yaml")
        self.videos_db = os.path.join(USER_CONFIG_DIR, "videos_db.yaml")

        # Load captures from persistent db
        self.images = self.load_capture_db(self.images_db)
        self.videos = self.load_capture_db(self.videos_db)

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

    # MANAGE CAPTURE DATABASE

    def save_capture_db(self, capture_list, db_path):
        capture_state = [capture.state for capture in capture_list]

        with open(db_path, 'w') as outfile:
            yaml.safe_dump(capture_state, outfile)

    def validate_captures(self, capture_list):
        # Purge captures with missing data files
        valid_captures = []
        for capture in capture_list:
            if capture.file_exists:
                valid_captures.append(capture)
            else:
                if os.path.isfile(capture.metadata_file):
                    logging.warning("Capture data missing. Deleting metadata file {}.".format(capture.metadata_file))
                    os.remove(capture.metadata_file)

        # Validate and repair captures
        for capture in valid_captures:
            # If the captures metadata file is missing
            if not os.path.isfile(capture.metadata_file):
                # Recreate the metadata file
                capture.save_metadata()
        
        return valid_captures

    def load_capture_db(self, db_path):
        if os.path.isfile(db_path):
            # Load list of capture dictionary representations from db_path
            with open(db_path, 'r') as infile:
                capture_dict_list = yaml.load(infile)

            # Create capture object list, and validate captures
            capture_list = self.validate_captures(
                [capture_from_dict(capture_dict) for capture_dict in capture_dict_list]
            )

            return capture_list

        else:
            return []

    # CREATING NEW CAPTURES

    def shunt_captures(self, target_list: list):
        for obj in target_list:  # For each older capture
            obj.shunt()  # Shunt capture from memory to storage

    def new_image(
            self,
            write_to_file: bool=False,
            temporary: bool=True,
            filename: str=None,
            fmt: str='jpeg',
            shunt_others: bool=True):

        """
        Create a new image capture object. Adds to the image list, and shunt all others.

        Args:
            write_to_file (bool): Should the StreamObject write to a file, or an in-memory byte stream.
            keep_on_disk (bool): Should the data be deleted after session ends. Creating the capture with a content manager sets this to true.
            filename (str): Name of the stored file. Defaults to timestamp.
            fmt (str): Format of the capture.
        """

        # Generate file name
        if not filename:
            filename = generate_basename(self.images)
            logging.debug(filename)

        # Create capture object
        output = CaptureObject(
            write_to_file=write_to_file,
            temporary=temporary,
            filename=filename,
            folder=self.paths['image'],
            fmt=fmt)

        # Update capture list
        self.shunt_captures(self.images)
        self.images.append(output)

        # Update capture database
        self.save_capture_db(self.images, self.images_db)

        return output

    def new_video(
            self,
            write_to_file: bool=True,
            temporary: bool=False,
            filename: str=None,
            fmt: str='h264',
            shunt_others: bool=True):

        """
        Create a new video capture object. Adds to the image list, and shunt all others.

        Args:
            write_to_file (bool): Should the StreamObject write to a file, or an in-memory byte stream.
            temporary (bool): Should the data be deleted after session ends. Creating the capture with a content manager sets this to true.
            filename (str): Name of the stored file. Defaults to timestamp.
            fmt (str): Format of the capture.
        """

        # Generate file name
        if not filename:
            filename = generate_basename(self.videos)
            logging.debug(filename)

        # Create capture object
        output = CaptureObject(
            write_to_file=write_to_file,
            temporary=temporary,
            filename=filename,
            folder=self.paths['video'],
            fmt=fmt)

        # Update capture list
        self.shunt_captures(self.videos)
        self.videos.append(output)

        # Update capture database
        self.save_capture_db(self.videos, self.videos_db)

        return output

    # WORKER THREAD

    def _thread(self):
        """Camera background thread."""
        self.frames_iterator = self.frames()
        logging.debug("Entering worker thread.")

        self.state['stream_active'] = True

        for frame in self.frames_iterator:
            self.frame = frame
            self.event.set()  # send signal to clients
            time.sleep(0)

            # Handle timeout
            if (
                self.stream_timeout_enabled and  # If using timeout
                (time.time() - self.last_access > self.stream_timeout) and  # And timeout time
                not self.state['preview_active']  # And GPU preview is not active
            ):
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
        # Set stream_activate state
        self.state['stream_active'] = False
        # Reset thread
        self.thread = None
