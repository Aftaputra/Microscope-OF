import uuid
import io
import os
import glob
import datetime
import copy
import logging
from PIL import Image
import atexit

pil_formats = ['JPG', 'JPEG', 'PNG', 'TIF', 'TIFF']
thumbnail_size = (60, 60)

BASE_CAPTURE_PATH = os.path.join(os.path.expanduser('~'), 'micrographs')
TEMP_CAPTURE_PATH = os.path.join(BASE_CAPTURE_PATH, 'tmp')

def clear_tmp():
    global TEMP_CAPTURE_PATH

    logging.info("Clearing {}...".format(TEMP_CAPTURE_PATH))
    files = glob.glob('{}/*'.format(TEMP_CAPTURE_PATH))
    for f in files:
        os.remove(f)
        logging.debug("Removed {}".format(f))

class CaptureObject(object):
    """
    StreamObject used to store and process capture data, and metadata.

    Note: Captures cannot be stored in a lower-level directory than BASE_CAPTURE_PATH.
    """
    def __init__(
            self,
            write_to_file: bool=False,
            keep_on_disk: bool=True,
            filename: str='',
            folder: str='',
            fmt: str='') -> None:
        """Create a new StreamObject, to manage capture data."""

        # Store a nice ID
        self.id = uuid.uuid4().hex
        logging.info("Created StreamObject {}".format(self.id))
        self.timestring = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Store file format
        self.format = fmt

        # Keep on disk after close by default
        self.keep_on_disk = keep_on_disk

        # Explicitally state if capture should be written to a file, not a bytestream
        self.write_to_file = write_to_file

        # Create file name. Default to UUID
        if not filename:
            filename = self.id

        self.filename = "{}.{}".format(filename, fmt)
        self.folder = folder

        # Initialise the capture stream
        self.initialise_capture()

        # Log if created by context manager
        self.context_manager = False

        # Object lock
        self.locked = False

        # Thumbnail (populated only for PIL captures)
        self.thumb_bytes = None

    def __enter__(self):
        """Create StreamObject in context, to auto-clean disk data."""
        logging.debug("Entering context for {}. Stored files will be cleaned up automatically regardless of location.".format(self.id))
        self.keep_on_disk = False  # Flag file to be removed on close.
        self.context_manager = True  # Used in metadata

        logging.info("Rebuilding as a temporary capture...")
        self.initialise_capture()

        return self

    def __exit__(self, *args):
        """Exit StreamObject, and auto-clean disk data."""
        logging.info("Cleaning up {}".format(self.id))
        self.close()

    def initialise_capture(self):
        self.build_file_path(self.filename, self.folder)

        # Byte bytestream properties
        self.bytestream = io.BytesIO()  # Byte bytestream that data will be written to

        # Set default write target
        if not self.write_to_file:
            logging.debug("Target for {} set to 'bytestream'".format(self.id))
            self.stream = self.bytestream
        else:
            logging.debug("Target for {} set to 'file'".format(self.id))
            self.stream = self.file

    def build_file_path(
            self,
            filename: str,
            folder: str):
        """
        Construct a full file path, based on filename, folder, and file format.

        Defaults to UUID.
        """
        global TEMP_CAPTURE_PATH

        self.file = os.path.join(folder, filename)  # Full file name by joining given folder to given name

        self.split_file_path(self.file)  # Split file path into folder, filename, and basename

        # Check directory is a subdirectory of BASE_CAPTURE_PATH
        if not os.path.commonprefix([self.file, BASE_CAPTURE_PATH]) == BASE_CAPTURE_PATH:
            raise Exception("Captures cannot be stored in a lower-level directory than {}.".format(BASE_CAPTURE_PATH))

        # Move to tmp directory if not being kept
        if not self.keep_on_disk:
            # TODO: Empty tmp folder on module load and atexit
            self.file_notmp = self.file  # Store originally defined folder
            self.filefolder = TEMP_CAPTURE_PATH
            self.file = os.path.join(self.filefolder, self.filename)

        # Create folder and file
        if not os.path.exists(self.filefolder):
            os.makedirs(self.filefolder)

        logging.debug(self.file)
        logging.debug(self.filename)
        logging.debug(self.basename)
        logging.debug(self.filefolder)

    def split_file_path(self, filepath):
        """Takes a full file path, and splits it into separated class properties."""
        self.filefolder, self.filename = os.path.split(filepath)  # Split the full file path into a folder and a filename
        self.basename = os.path.splitext(self.filename)[0]  # Split the filename out from it's file extension

    def lock(self):
        """Set locked flag to True."""
        self.locked = True

    def unlock(self):
        """Set locked flag to False."""
        self.locked = False

    @property
    def stream_exists(self, auto_rewind=True) -> bool:
        """Check if BytesIO bytestream is empty."""
        if auto_rewind:
            self.bytestream.seek(0)  # Rewind the data bytes for reading
        if self.bytestream.getvalue():  # If data bytestream contains data
            self.bytestream.seek(0)  # Rewind the data bytes for reading
            return True
        else:
            self.bytestream.seek(0)  # Rewind the data bytes for reading
            return False

    @property
    def file_exists(self) -> bool:
        """Check if corresponding file exists."""
        if os.path.isfile(self.file):
            return True
        else:
            return False

    @property
    def metadata(self) -> dict:
        """Return dictionary of StreamObject properties."""
        d = {
            'id': self.id,
            'locked': self.locked,
            'keep_on_disk': self.keep_on_disk,
            'filename': self.filename,
            'path': self.file,
            'time': self.timestring
        }

        # Check bytestream
        if self.stream_exists:
            d['bytestream'] = True
        else:
            d['bytestream'] = False

        # Combined availability of data
        if self.stream_exists or self.file_exists:
            d['available'] = True
        else:
            d['available'] = False

        # Check if file was manually deleted
        if self.keep_on_disk and not self.file_exists:
            d['path'] = "{} (Deleted)".format(d['path'])

        return d

    @property
    def data(self) -> io.BytesIO:
        """Return a byte string of the capture data."""
        self.bytestream.seek(0)  # Rewind the data bytes for reading

        if self.stream_exists:  # If data bytestream contains data
            # Create a copy of the bytestream bytes
            data = io.BytesIO(self.bytestream.getbuffer())

        else:  # If data bytestream is empty
            if self.file_exists:  # If data file exists
                logging.info("Opening from file {}".format(self.file))
                with open(self.file, 'rb') as f:
                    d = io.BytesIO(f.read())  # Load bytes from file
                d.seek(0)  # Rewind loaded bytestream
                # Create a copy of the bytestream bytes
                data = io.BytesIO(d.getbuffer())
            else:
                data = None

        return data  # Read and return bytes data

    @property
    def binary(self) -> bytes:
        """Return a byte string of the capture data."""
        return self.data.getvalue()

    @property
    def thumbnail(self) -> io.BytesIO:
        # If no thumbnail exists, try and make one
        if not self.thumb_bytes:
            logging.info("Building thumbnail")
            if self.format.upper() in pil_formats:
                im = Image.open(self.data)
                im.thumbnail(thumbnail_size)

                self.thumb_bytes = io.BytesIO()
                im.save(self.thumb_bytes, self.format)
                self.thumb_bytes.seek(0)
        else:
            self.thumb_bytes.seek(0)

        # Copy the buffer, to avoid closing the file
        data = io.BytesIO(self.thumb_bytes.getbuffer())
        return data

    def load_file(self) -> bool:
        """Load data stored on disk to the in-memory bytestream."""
        if self.file_exists:  # If data file exists
            with open(self.file, 'rb') as f:
                self.bytestream = io.BytesIO(f.read())  # Load bytes from file
            self.bytestream.seek(0)  # Rewind data bytes again
            return True
        else:
            return False

    def save_file(self) -> bool:
        """Write the StreamObjects bytestream to a file."""
        if not self.keep_on_disk:  # If capture is currently temporary
            self.load_file()  # Load data from tmp file into bytestream, if tmp file exists
            self.keep_on_disk = True  # Flag as kept on disk
            self.file = self.file_notmp  # Reset file path to non-temporary path
            self.split_file_path(self.file)  # Set split properties based on new path
            logging.info("Moved temporary file out to {}".format(self.file))

        if self.stream_exists:  # If there's a bytestream to save
            with open(self.file, 'ab') as f:  # Load file as bytes
                logging.debug("Writing bytestream to file {}".format(self.file))
                f.seek(0, 0)  # Seek to the start of the file
                f.write(self.binary)  # Write data bytes to file
            return True
        else:
            return False

    def delete_stream(self):
        """Clear the BytesIO bytestream of the StreamObject."""
        self.bytestream = io.BytesIO()

    def delete_file(self) -> bool:
        """If the StreamObject has been saved, delete the file."""
        if os.path.isfile(self.file):
            logging.info("Deleting file {}".format(self.file))
            os.remove(self.file)
            return True
        else:
            return False

    def delete(self):
        """Entirely delete all capture data."""
        logging.info("Deleting {}".format(self.id))
        self.delete_stream()
        self.delete_file()

    def shunt(self):
        """Demote the StreamObject from being stored in memory."""
        if not self.file_exists:  # If file doesn't already exist
            self.save_file()  # Save bytestream to disk, if it exists
        self.delete_stream()  # Delete the bytestream from memory

    def close(self):
        """Both clear the bytestream, and delete any associated on-disk data."""
        logging.info("Closing {}".format(self.id))
        self.delete_stream()
        if not self.keep_on_disk:
            self.delete_file()

atexit.register(clear_tmp)