#!/usr/bin/env python
from api_client import APIconnection

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
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


class TestCapture(unittest.TestCase):

    def test_capture_config(self):
        connection = APIconnection(host="localhost", port=5000, api_ver="v1")
        config = connection.get_config()
        
        expected_keys = [
            'image_resolution',
            'video_resolution',
            'numpy_resolution',
        ]

        for key in expected_keys:
            self.assertTrue(key in config)

    def test_capture_videoport(self):
        connection = APIconnection(host="localhost", port=5000, api_ver="v1")
        resolution = connection.get_config()['video_resolution']

        capture_array = connection.capture(
            use_video_port=True, 
            keep_on_disk=False, 
            delete_after_use=True)

        self.assertTrue(capture_array.shape == (resolution[1], resolution[0], 3))

    def test_capture_full(self):
        connection = APIconnection(host="localhost", port=5000, api_ver="v1")
        resolution = connection.get_config()['image_resolution']

        capture_array = connection.capture(
            use_video_port=False, 
            keep_on_disk=False, 
            delete_after_use=True)

        self.assertTrue(capture_array.shape == (resolution[1], resolution[0], 3))

class TestStage(unittest.TestCase):

    def test_stage_config(self):
        connection = APIconnection(host="localhost", port=5000, api_ver="v1")
        config = connection.get_config()
        
        expected_keys = [
            'backlash',
        ]

        for key in expected_keys:
            self.assertTrue(key in config)

if __name__ == '__main__':

    suites = [
        unittest.TestLoader().loadTestsFromTestCase(TestCapture),
        unittest.TestLoader().loadTestsFromTestCase(TestStage),
    ]

    alltests = unittest.TestSuite(suites)

    result = unittest.TextTestRunner(verbosity=2).run(alltests)
