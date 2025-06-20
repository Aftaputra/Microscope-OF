from PIL import Image
import piexif
import json
import numpy as np

from labthings_fastapi.dependencies.metadata import GetThingStates
from labthings_fastapi.thing import Thing
from labthings_fastapi.dependencies.raw_thing import raw_thing_dependency
from .camera import CameraDependency as CamDep
from labthings_fastapi.dependencies.invocation import (
    InvocationLogger,
)


class CaptureError(RuntimeError):
    """An error trying to capture from Picamera"""


class CaptureThing(Thing):
    """A temporary Thing to handle capturing to disk with associated metadata
    Will be moved to the camera Thing or dependency in due course"""

    def _capture_image(
        self, cam: CamDep, metadata_getter: GetThingStates
    ) -> tuple[np.ndarray, dict]:
        """Capture an image in memory and return it with metadata
        CaptureError raised if the capture fails for any reason
        returns tuple with numpy array of image data, and dict of metadata
        """
        try:
            metadata = metadata_getter()
            image = cam.capture_array()[..., :3]
        except Exception as e:
            raise CaptureError("An error occurred while capturing") from e
        return image, metadata

    def _save_capture(
        self,
        jpeg_path: str,
        image: Image.Image,
        metadata: dict,
        logger: InvocationLogger,
    ) -> None:
        """Saving the captured image and metadata to disk
        logger warning (via InvocationLogger) is raised if metadata is failed to be added
        IOError is raised if the file cannot be saved
        nothing is returned on success"""
        try:
            Image.fromarray(image.astype("uint8"), "RGB").save(
                jpeg_path, quality=95, subsampling=0
            )
            try:
                exif_dict = piexif.load(jpeg_path)
                exif_dict["Exif"][piexif.ExifIFD.UserComment] = json.dumps(
                    metadata
                ).encode("utf-8")
                piexif.insert(piexif.dump(exif_dict), jpeg_path)
            except:  # noqa: E722
                # We need to capture any exception as there are many reasons metadata
                # might not be added. We warn rather than log the error.
                logger.warning(f"Failed to add metadata to {jpeg_path}")
        except Exception as e:
            raise IOError(f"An error occurred while saving {jpeg_path}") from e


RawCaptureDependency = raw_thing_dependency(CaptureThing)
