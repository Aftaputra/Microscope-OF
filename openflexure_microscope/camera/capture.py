import uuid
import io
import os
import datetime
import copy
import logging


class StreamObject(object):
    def __init__(
            self,
            write_to_file: bool=None,
            keep_on_disk: bool=True,
            filename: str=None,
            folder: str=None,
            fmt: str='file') -> None:
        """Create a new StreamObject, to manage capture data."""
        # Store a nice ID
        self.id = uuid.uuid4().hex
        logging.info("Created {}".format(self.id))

        # Create file name
        iterator = 0
        f_path, f_name = self.build_file_path(filename, folder, fmt)

        while os.path.isfile(f_name):  # While file already exists
            iterator += 1  # Add a file name iterator
            f_path, f_name = self.build_file_path(
                filename,
                folder,
                fmt,
                iterator=iterator)  # Rebuild file name

        self.file = f_path
        self.filename = f_name

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

        # Keep on disk after close by default
        self.keep_on_disk = keep_on_disk

        # Log if created by context manager
        self.context_manager = False

        # Object lock
        self.locked = False

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
            fmt: str,
            iterator: int=0) -> str:
        """
        Construct a full file path, based on filename, folder, and file format.

        Defaults to datestamp. 
        Iterator adds a numeric increment to the file name.
        """
        if filename:
            file_name = "{}.{}".format(filename, fmt)
        else:
            file_name_base = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            if iterator:
                file_name_base = "{}_{}".format(file_name_base, iterator)
            file_name = "{}.{}".format(file_name_base, fmt)

        # Create folder and file
        if folder:
            if not os.path.exists(folder):
                os.mkdir(folder)

            file_path = os.path.join(folder, file_name)
        else:
            file_path = file_name

        return (file_path, file_name)

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
            'path': self.file,
            'context_manager': self.context_manager,
        }

        # Get file path
        if self.file_exists:
            d['file'] = self.filename
        else:
            d['file'] = None

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
                # TODO: Streamline this bit
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

    def load_file(self) -> bool:
        """Load data stored on disk to the in-memory stream."""
        if self.file_exists:  # If data file exists
            # TODO: Streamline this bit
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
