#!/usr/bin/env python
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage
from openflexure_microscope import Microscope, config

import atexit
import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

if __name__ == '__main__':
    openflexurerc = config.load_config()

    microscope = Microscope(StreamingCamera(config=openflexurerc), OpenFlexureStage("/dev/ttyUSB0"))

    microscope.find_plugins()  # Automatically find microscope plugins

    # Check that default tets plugins have loaded
    print("RUNNING PLUGIN METHODS:")
    microscope.plugin.test1.run()
    microscope.plugin.test2.run()

    microscope.close()
