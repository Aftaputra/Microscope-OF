from openflexure_microscope.stage.sangaboard import Sangaboard

import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

stage = Sangaboard()