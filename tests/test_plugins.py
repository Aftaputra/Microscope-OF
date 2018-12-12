#!/usr/bin/env python
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage
from openflexure_microscope import Microscope, config

import atexit
import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

if __name__ == '__main__':
    openflexurerc = config.load_config()

    print(openflexurerc)

    microscope = Microscope(StreamingCamera(config=openflexurerc), OpenFlexureStage("/dev/ttyUSB0"), config=openflexurerc)

    print(microscope.plugin.plugins)

    # Check that default tets plugins have loaded
    print(microscope.plugin.default.identify())

    microscope.close()
