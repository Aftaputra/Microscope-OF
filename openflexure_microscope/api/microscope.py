from openflexure_microscope import Microscope
from openflexure_microscope.camera.capture import build_captures_from_exif

import logging

# Import device modules
# NB this will eventually be handled by the RC file, so you can choose what device
# class should be attached.
try:
    from openflexure_microscope.camera.pi import PiCameraStreamer
except ImportError:
    logging.warning("Unable to import PiCameraStreamer")
from openflexure_microscope.camera.mock import MockStreamer

from openflexure_microscope.stage.sanga import SangaStage
from openflexure_microscope.stage.mock import MockStage

default_microscope = Microscope()

# Initialise camera
logging.debug("Creating camera object...")
try:
    api_camera = PiCameraStreamer()
except Exception as e:
    logging.error(e)
    logging.warning("No valid camera hardware found. Falling back to mock camera!")
    api_camera = MockStreamer()

# Initialise stage
logging.debug("Creating stage object...")

api_stage = MockStage()

# Attach devices to microscope
logging.debug("Attaching devices to microscope...")
default_microscope.attach(api_camera, api_stage)

# Restore loaded capture array to camera object
logging.debug("Restoring captures...")
default_microscope.camera.images = build_captures_from_exif(
    default_microscope.camera.paths["default"]
)

logging.debug("Microscope successfully attached!")
