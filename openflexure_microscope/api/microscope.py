import logging

from openflexure_microscope.microscope import Microscope

default_microscope = Microscope()

# Restore loaded capture array to camera object
logging.debug("Restoring captures...")
default_microscope.captures.rebuild_captures()

logging.debug("Microscope successfully attached!")
