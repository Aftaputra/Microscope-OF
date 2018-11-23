#!/usr/bin/env python
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage
from openflexure_microscope import Microscope
from openflexure_microscope.plugins import PluginMount, load_plugin, search_plugin_dirs

import atexit
import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

if __name__ == '__main__':
    microscope = Microscope(StreamingCamera(), OpenFlexureStage("/dev/ttyUSB0"))

    plugins_list = search_plugin_dirs([], include_default=True)

    for i in plugins_list:
        module = load_plugin(i)
        microscope.plugin.attach(module)

    # Check that default tets plugins have loaded
    print("RUNNING PLUGIN METHODS:")
    microscope.plugin.test1.run()
    microscope.plugin.test2.run()

    microscope.close()