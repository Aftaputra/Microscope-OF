from openflexure_microscope import Microscope
from openflexure_microscope.camera.capture import build_captures_from_exif

import logging


default_microscope = Microscope()

# Restore loaded capture array to camera object
logging.debug("Restoring captures...")
default_microscope.camera.images = build_captures_from_exif(
    default_microscope.camera.paths["default"]
)

logging.debug("Microscope successfully attached!")
