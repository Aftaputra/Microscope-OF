#!/usr/bin/env python
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage
from openflexure_microscope import Microscope, config

import atexit

import unittest

import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

success_string = """
            /O
           | |
      _____) \\
     (__0)    \\______
    (____0)
    (____0)        EVERYTHING IS OK!
     (__o)___________
    """

class TestPluginMethods(unittest.TestCase):

    def test_testplugin_load(self):
        plugin_arr = microscope.plugin.plugins

        plugin_names = [plugin[0] for plugin in plugin_arr]

        self.assertTrue('testing' in plugin_names)

    def test_camera_access(self):
        identify = microscope.plugin.testing.identify()
        self.assertTrue(identify[0] is microscope.camera)

    def test_stage_access(self):
        identify = microscope.plugin.testing.identify()
        self.assertTrue(identify[1] is microscope.stage)


if __name__ == '__main__':

    openflexurerc = {
        'plugins': [
            'openflexure_microscope.plugins.testing:Plugin'
        ]
    }

    with StreamingCamera() as camera, OpenFlexureStage("/dev/ttyUSB0") as stage:

        microscope = Microscope(camera, stage, openflexurerc)

        suites = [
            unittest.TestLoader().loadTestsFromTestCase(TestPluginMethods),
        ]

        alltests = unittest.TestSuite(suites)

        result = unittest.TextTestRunner(verbosity=2).run(alltests)

        if result.wasSuccessful():
            print(success_string)

    microscope.close()