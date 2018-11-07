#!/usr/bin/env python
from openflexure_microscope.camera.pi import StreamingCamera
from openflexure_stage import OpenFlexureStage
from openflexure_microscope import Microscope

import os
import io
import sys
import time
import numpy as np
import uuid

from PIL import Image

import unittest
from pprint import pprint

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


class TestMicroscope(unittest.TestCase):

    def test_startup(self):
        """Tests capturing still images to a BytesIO stream."""
        global microscope
        pass


if __name__ == '__main__':
    with StreamingCamera() as camera, OpenFlexureStage(None) as stage:

        microscope = Microscope(camera, stage)

        suites = [
            unittest.TestLoader().loadTestsFromTestCase(TestMicroscope),
        ]

        alltests = unittest.TestSuite(suites)

        result = unittest.TextTestRunner(verbosity=2).run(alltests)

        if result.wasSuccessful():
            print(success_string)

