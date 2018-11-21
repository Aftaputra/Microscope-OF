import uuid
import io
import os
import datetime
import copy
import logging
from PIL import Image

pil_formats = ['JPG', 'JPEG', 'PNG', 'TIF', 'TIFF']
thumbnail_size = (60, 60)


class StreamObject(object):
    """
    StreamObject used to store and process capture data, and metadata.
    """
    def __init__(
            self,
            write_to_file: bool=False,
            keep_on_disk: bool=True,
            filename: str=None,
            folder: str=None,
            fmt: str='file') -> None:
        """Create a new StreamObject, to manage capture data."""
        # Store a nice ID
        self.id = uuid.uuid4().hex
        logging.info("Created StreamObject {}".format(self.id))
        self.timestring = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Store file format
        self.format = fmt

        # Keep on disk after close by default
        self.keep_on_disk = keep_on_disk

        # Create file name. Default to UUID
        if not filename:
            filename = self.id
        self.build_file_path(filename, folder, self.format)

        # Byte stream properties
        self.stream = io.BytesIO()  # Byte stream that data will be written to

        # Set default write target
        self.write_to_file = write_to_file
        if self.write_to_file is False:
            logging.debug("Target for {} set to 'stream'".format(self.id))
            self.target = self.stream
        else:
            logging.debug("Target for {} set to 'file'".format(self.id))
            self.target = self.file

        # Log if created by context manager
        self.context_manager = False

        # Object lock
        self.locked = False

        # Thumbnail (populated only for PIL captures)
        self.thumb_bytes = None

    def __enter__(self):
        """Create StreamObject in context, to auto-clean disk data."""
        logging.debug("Entering context for {}.\
            Stored files will be cleaned up automatically.".format(self.id))
        self.keep_on_disk = False  # Flag file to be removed on close.
        self.context_manager = True  # Used in metadata
        return self

    def __exit__(self, *args):
        """Exit StreamObject, and auto-clean disk data."""
        logging.info("Cleaning up {}".format(self.id))
        self.close()

    def build_file_path(
            self,
            filename: str,
            folder: str,
            fmt: str):
        """
        Construct a full file path, based on filename, folder, and file format.

        Defaults to datestamp.
        """

        base_name = filename
        file_name = "{}.{}".format(base_name, fmt)

        # Create folder and file
        if folder:
            if not os.path.exists(folder):
                os.mkdir(folder)

            file_path = os.path.join(folder, file_name)
        else:
            file_path = file_name

        # Handle path appendix
        appendix = ""
        if not self.keep_on_disk:
            appendix += ".tmp"

        file_path = file_path + appendix

        #self.basename = filename
        self.file = file_path
        self.filename = file_name
        self.basename = base_name

    def lock(self):
        """Set locked flag to True."""
        self.locked = True

    def unlock(self):
        """Set locked flag to False."""
        self.locked = False

    @property
    def stream_exists(self, auto_rewind=True) -> bool:
        """Check if BytesIO stream is empty."""
        if auto_rewind:
            self.stream.seek(0)  # Rewind the data bytes for reading
        if self.stream.getvalue():  # If data stream contains data
            self.stream.seek(0)  # Rewind the data bytes for reading
            return True
        else:
            self.stream.seek(0)  # Rewind the data bytes for reading
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

        # Check stream
        if self.stream_exists:
            d['stream'] = True
        else:
            d['stream'] = False

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
        self.stream.seek(0)  # Rewind the data bytes for reading

        if self.stream_exists:  # If data stream contains data
            # Create a copy of the stream bytes
            data = io.BytesIO(self.stream.getbuffer())

        else:  # If data stream is empty
            if self.file_exists:  # If data file exists
                logging.info("Opening from file {}".format(self.file))
                with open(self.file, 'rb') as f:
                    d = io.BytesIO(f.read())  # Load bytes from file
                d.seek(0)  # Rewind loaded stream
                # Create a copy of the stream bytes
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
        """Load data stored on disk to the in-memory stream."""
        if self.file_exists:  # If data file exists
            with open(self.file, 'rb') as f:
                self.stream = io.BytesIO(f.read())  # Load bytes from file
            self.stream.seek(0)  # Rewind data bytes again
            return True
        else:
            return False

    def save_file(self) -> bool:
        """Write the StreamObjects stream to a file."""
        if self.stream_exists:  # If there's a stream to save
            with open(self.file, 'ab') as f:  # Load file as bytes
                logging.debug("Writing stream to file {}".format(self.file))
                f.seek(0, 0)  # Seek to the start of the file
                f.write(self.binary)  # Write data bytes to file
            return True
        else:
            return False

    def delete_stream(self):
        """Clear the BytesIO stream of the StreamObject."""
        self.stream = io.BytesIO()

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
            self.save_file()  # Save stream to disk, if it exists
        self.delete_stream()  # Delete the stream from memory

    def close(self):
        """Both clear the stream, and delete any associated on-disk data."""
        logging.info("Closing {}".format(self.id))
        self.delete_stream()
        if not self.keep_on_disk:
            self.delete_file()
