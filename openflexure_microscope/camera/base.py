import time
import os
import io
import threading
import copy
import datetime
from PIL import Image

try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident

# Slightly crappy debugger logging
DEBUG = True


def log(s):
    if DEBUG:
        print('DEBUG: {}'.format(s))


class StreamObject(object):
    def __init__(self, write_to_file: bool=None, filename: str=None, folder: str=None, fmt: str='file') -> None:
        # Store a nice ID
        self.id = filename
        log("Created {}".format(self.id))

        # Create file name
        self.file = self.build_file_path(filename, folder, fmt)

        # Byte stream properties
        self.stream = io.BytesIO()  # Byte stream that data will be written to

        # Set default write target
        self.write_to_file = write_to_file
        if self.write_to_file == False:
            log("Default target for {} set to 'stream'".format(self.id))
            self.target = self.stream
        else:
            log("Default target for {} set to 'file'".format(self.id))
            self.target = self.file

        # Object lock
        self.locked = False  # Is the StreamObject locked for writing? (Handled by StreamingCamera)

    def __enter__(self):
        log("Entering context for {}. Stored files will be cleaned up automatically.".format(self.id))
        return self

    def __exit__(self, *args):
        log("Cleaning up {}".format(self.id))
        self.delete()

    def build_file_path(self, filename: str, folder: str, fmt: str) -> str:
        """
        Construct a full file path, based on filename, folder, and file format. Defaults to datestamp
        """
        if filename:
            file_name = "{}.{}".format(filename, fmt)
        else:
            file_name = "{}.{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), fmt)

        # Create folder and file 
        if folder:
            if not os.path.exists(folder):
                os.mkdir(folder)

            file_path = os.path.join(folder, file_name)
        else:
            file_path = file_name

        return file_path

    def lock(self):
        """Set locked flag to True"""
        self.locked = True

    def unlock(self):
        """Set locked flag to False"""
        self.locked = False

    @property
    def data(self) -> io.BytesIO:
        """Return a byte string of the capture data"""
        self.stream.seek(0)  # Rewind the data bytes for reading

        if not self.stream.getvalue() and os.path.isfile(self.file):  # If stream is empty but file is not
            log("No stream data. Opening from file {}".format(self.file))
            with open(self.file, 'rb') as f:
                self.stream = io.BytesIO(f.read())  # Load bytes from file in disk
            self.stream.seek(0)  # Rewind data bytes again
        
        data = self.stream.getbuffer()  # Create a copy of the stream bytes

        return io.BytesIO(data)  # Read and return bytes data

    @property
    def binary(self) -> bytes:
        """Return a byte string of the capture data"""
        return self.data.getvalue()

    def save(self):
        """
        Creates/opens a file, and writes this StreamObjects bytestring to the file.
        """
        with open(self.file, 'ab') as f:  # Load file as bytes
            log("Writing stream to file {}".format(self.file))
            f.seek(0, 0)  # Seek to the start of the file
            f.write(self.binary)  # Write data bytes to file

    def clear_stream(self):
        """Clears the BytesIO stream of the StreamObject."""
        self.stream = io.BytesIO()
        return True

    def delete(self) -> bool:
        """
        If the StreamObject has been saved to disk, deletes the file and returns True.
        """
        if os.path.isfile(self.file):
            log("Deleting file {}".format(self.file))
            os.remove(self.file)
            return True
        else:
            log("File not found {}".format(self.file))
            return False


class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        self.events = {}

    def wait(self, timeout: int=5):
        """Invoked from each client's thread to wait for the next frame."""
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait(timeout)

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
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
        """Invoked from each client's thread after a frame was processed."""
        self.events[get_ident()][0].clear()


class BaseCamera(object):
    thread = None  # Background thread that reads frames from camera
    camera = None  # Camera object, for direct access to camera

    frame = None  # Current frame is stored here by background thread
    last_access = 0  # Time of last client access to the camera
    event = CameraEvent()
    
    def __init__(self):
        self.start_worker()

        # Stores state of StreamingCamera
        self.state = {
        }

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
            log("Waiting for frames")
            while self.get_frame() is None:
                if time.time() > timeout_time:
                    raise TimeoutError("Timeout waiting for frames.")
                    break
                else:
                    time.sleep(0)
        return True

    def stop_worker(self, timeout: int=5) -> bool:
        """Flags worker thread for stop. Waits for thread to close, or times out."""
        timeout_time = time.time() + timeout

        self.stop = True
        while self.thread:
            if time.time() > timeout_time:
                raise TimeoutError("Timeout waiting for worker thread to close.")
                break
            else:
                time.sleep(0)
        return True

    def get_frame(self):
        """Return the current camera frame."""
        self.last_access = time.time()

        # wait for a signal from the camera thread
        self.event.wait()
        self.event.clear()

        return self.frame

    def frames(self):
        """Generator that returns frames from the camera."""
        raise RuntimeError('Must be implemented by subclasses.')

    def close(self):
        """Handles closing the StreamingCamera"""
        self.stop_worker()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close camera stream on context exit."""
        self.close()

    def _thread(self):
        """Camera background thread."""
        self.frames_iterator = self.frames()

        # Update state
        self.state['stream_active'] = True

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
                    self.frames_iterator.close()
                    break
                    
            except AttributeError:
                pass
    
        # Reset thread
        self.thread = None
        # Destroy any stored camera object (used especially for handling Pi cameras)
        self.camera = None
        # Update state
        self.state['stream_active'] = False