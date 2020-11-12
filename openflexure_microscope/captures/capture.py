import datetime
import glob
import io
import json
import logging
import os
import uuid
from collections import OrderedDict

import dateutil.parser
from PIL import Image

from openflexure_microscope.captures import piexif
from openflexure_microscope.captures.piexif import InvalidImageDataError
from openflexure_microscope.json import JSONEncoder

EXIF_FORMATS = ["JPG", "JPEG", "TIF", "TIFF"]
THUMBNAIL_SIZE = (200, 150)


def make_file_list(directory, formats):
    files = []
    for fmt in formats:
        files.extend(
            glob.glob("{}/**/*.{}".format(directory, fmt.lower()), recursive=True)
        )

    logging.info("{} capture files found on disk".format(len(files)))

    return files


def build_captures_from_exif(capture_path):
    logging.debug("Reloading captures from {}...".format(capture_path))
    files = make_file_list(capture_path, EXIF_FORMATS)
    captures = OrderedDict()

    for f in files:
        logging.debug("Reloading capture {}...".format(f))
        capture = capture_from_path(f)
        if capture:
            captures[capture.id] = capture

    logging.info("{} capture files successfully reloaded".format(len(captures)))

    return captures


def capture_from_path(path):
    # Create a placeholder capture
    capture = CaptureObject(filepath=path)

    # Build file path information
    capture.split_file_path(capture.file)

    # Check and sync basic metadata
    try:
        capture.sync_basic_metadata()
        return capture
    except (InvalidImageDataError, json.decoder.JSONDecodeError):
        logging.error("Invalid metadata at {}.".format(path))
        return None


class CaptureObject(object):
    """
    File-like object used to store and process on-disk capture data, and metadata.
    Serves to simplify modifying properties of on-disk capture data.
    """

    def __init__(self, filepath) -> None:
        """Create a new StreamObject, to manage capture data."""
        # Stream for buffering capture data
        self.stream = io.BytesIO()

        # Store a nice ID
        self.id = uuid.uuid4()  #: str: Unique capture ID
        logging.debug("Created CaptureObject {}".format(self.id))

        self.time = datetime.datetime.now()

        # Create file name. Default to UUID
        self.format = None
        self.file = filepath
        self.split_file_path(self.file)

        if not os.path.exists(self.filefolder):
            os.makedirs(self.filefolder)

        # Dataset information
        self._dataset = None
        # Dictionary for storing custom annotations
        # Can be modified via the web API
        self.annotations = {}
        # List for storing tags
        # Can be modified via the web API
        self.tags = []

    def write(self, s):
        logging.debug("Writing to %s", self)
        self.stream.write(s)

    def flush(self):
        logging.info("Writing image data to disk %s", self.file)
        with open(self.file, "wb") as outfile:
            outfile.write(self.stream.getbuffer())
        self.stream.close()
        logging.info("Writing metadata to disk %s", self.file)
        self._init_metadata()
        logging.info("Finished writing to disk %s", self.file)

    def open(self, mode):
        return open(self.file, mode)

    def split_file_path(self, filepath):
        """
        Take a full file path, and split it into separated class properties.

        Args:
            filepath (str): String of the full file path, including file format extension
        """
        # Split the full file path into a folder and a name
        self.filefolder, self.name = os.path.split(filepath)
        # Split the name out from it's file extension
        self.basename = os.path.splitext(self.name)[0]
        self.format = self.name.split(".")[-1]

    def _read_exif(self):
        return piexif.load(self.file)

    def _decode_usercomment(self, exif_dict: dict):
        if "Exif" not in exif_dict:
            raise InvalidImageDataError
        if piexif.ExifIFD.UserComment not in exif_dict["Exif"]:
            return {}
        return json.loads(exif_dict["Exif"][piexif.ExifIFD.UserComment].decode())

    def _init_metadata(self):
        self.put_and_save(
            metadata={
                "image": {
                    "id": self.id,
                    "name": self.name,
                    "time": self.time.isoformat(),
                    "format": self.format,
                    "tags": self.tags,
                    "annotations": self.annotations,
                }
            }
        )

    def sync_basic_metadata(self):
        exif_dict = self._read_exif()

        metadata_dict = self._decode_usercomment(exif_dict) or {}
        image_metadata = metadata_dict.get("image")

        if not image_metadata:
            raise InvalidImageDataError("No capture metadata found")

        self.id = image_metadata.get("id")
        self.format = image_metadata.get("format")
        self.time = dateutil.parser.isoparse(
            image_metadata.get("time") or image_metadata.get("acquisitionDate")
        )
        self.tags = image_metadata.get("tags")
        self.annotations = image_metadata.get("annotations")

        dataset = metadata_dict.get("dataset")
        if dataset:
            self._dataset = {
                "id": dataset.get("id"),
                "name": dataset.get("name"),
                "type": dataset.get("type"),
            }

    def read_full_metadata(self):
        logging.info("Reading full capture metadata from %s...", self.file)
        exif_dict = self._read_exif()
        return self._decode_usercomment(exif_dict)

    @property
    def dataset(self):
        """Read-only dataset property"""
        return self._dataset

    @property
    def exists(self) -> bool:
        """Check if capture data file exists on disk."""
        if os.path.isfile(self.file):
            return True
        else:
            return False

    # HANDLE TAGS
    def put_tags(self, tags: list):
        """
        Add a new tag to the ``tags`` list attribute.

        Args:
            tags (list): List of tags to be added
        """
        self.put_and_save(tags=tags)

    def delete_tag(self, tag: str):
        """
        Remove a tag from the ``tags`` list attribute, if it exists.

        Args:
            tag (str): Tag to be removed
        """
        # Update in-memory tag list
        if tag in self.tags:
            self.tags = [new_tag for new_tag in self.tags if new_tag != tag]

        # Write in-memory metadata to file
        self.put_and_save()

    # HANDLE ANNOTATIONS

    def put_annotations(self, data: dict) -> None:
        """
        Merge annotations from a passed dictionary into the capture metadata, and saves.

        Args:
            data (dict): Dictionary of metadata to be added
        """
        self.put_and_save(annotations=data)

    def delete_annotation(self, key: str) -> None:
        # Update in-memory annotations list
        if key in self.annotations:
            del self.annotations[key]

        # Write in-memory metadata to file
        self.put_and_save()

    # HANDLE METADATA

    def put_metadata(self, data: dict) -> None:
        """
        Merge root metadata from a passed dictionary into the capture metadata, and saves.

        Args:
            data (dict): Dictionary of metadata to be added
        """
        self.put_and_save(metadata=data)

    # BULK OPERATIONS

    def put_and_save(
        self, tags: list = None, annotations: dict = None, metadata: dict = None
    ):
        """
        Batch-write tags, metadata, and annotations in a single disk operation
        """
        if not tags:
            tags = []
        if not annotations:
            annotations = {}
        if not metadata:
            metadata = {}

        # Update in-memory tags array
        for tag in tags:
            if tag not in self.tags:
                self.tags.append(tag)

        # Update in-memory annotations dictionary
        self.annotations.update(annotations)

        # Write new data to file EXIF, if supported
        if self.format.upper() in EXIF_FORMATS and self.exists:
            logging.info("Writing Exif data to %s", self.file)

            # Extract current Exif data
            exif_dict = self._read_exif()
            metadata_dict = self._decode_usercomment(exif_dict) or {}

            # Add new tags to exif dictionary
            metadata_dict.get("image", {})["tags"] = self.tags
            # Add new annotations to exif dictionary
            metadata_dict.get("image", {})["annotations"] = self.annotations
            # Add new custom metadata to exif dictionary
            metadata_dict.update(metadata)

            # Serialize metadata
            metadata_string = json.dumps(metadata_dict, cls=JSONEncoder)
            logging.debug("Saving metadata string to file: %s", metadata_string)

            # Insert metadata into exif_dict
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = metadata_string.encode()

            # Convert new exif dict to exif bytes
            exif_bytes = piexif.dump(exif_dict)

            # Insert exif into file
            piexif.insert(exif_bytes, self.file)
            logging.info("Finished writing Exif data to %s", self.file)

    # PROPERTIES

    @property
    def metadata(self) -> dict:
        """
        Create basic metadata dictionary from basic capture data, 
        and any added custom metadata and tags.
        """
        # Add custom metadata to dictionary
        return self.read_full_metadata()

    @property
    def data(self) -> io.BytesIO:
        """
        Return a BytesIO object of the capture data.
        """

        if self.exists:  # If data file exists
            logging.info("Opening from file {}".format(self.file))
            with open(self.file, "rb") as f:
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
        """
        Returns a thumbnail of the capture data, for supported image formats.
        """
        exif_dict = piexif.load(self.file)
        thumbnail = exif_dict.pop("thumbnail")
        if thumbnail:
            return io.BytesIO(thumbnail)
        # If no thumbnail exists, make and save one
        thumb_bytes = io.BytesIO()
        thumb_im = Image.open(self.data)
        thumb_im.thumbnail(THUMBNAIL_SIZE)
        thumb_im.save(thumb_bytes, "jpeg")
        thumbnail = thumb_bytes.getvalue()
        exif_dict["thumbnail"] = thumbnail
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, self.file)
        return io.BytesIO(thumbnail)

    # FILE MANAGEMENT

    def save(self) -> None:
        """Write stream to file, and save/update metadata file"""
        # If a stream OR file exists, save the metadata file
        if self.exists:
            self.put_and_save()

    def delete(self) -> bool:
        """If the StreamObject has been saved, delete the file."""

        if os.path.isfile(self.file):
            logging.info("Deleting file {}".format(self.file))
            os.remove(self.file)

            return True
        else:
            return False

    def close(self):
        pass
