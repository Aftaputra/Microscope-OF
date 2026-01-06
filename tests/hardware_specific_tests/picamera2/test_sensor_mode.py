"""Test changing and setting camerat modes on the Raspberry Picamera."""

import logging

import numpy as np

from .cam_test_utils import camera_test_client

logging.basicConfig(level=logging.DEBUG)


def test_sensor_mode():
    """Test capturing raw arrays in two different sensor modes."""
    with camera_test_client() as client:
        for size in [(3280, 2464), (1640, 1232)]:
            client.sensor_mode = {"output_size": size, "bit_depth": 10}
            arr = np.array(client.capture_array(stream_name="raw"))
            # Check that the array dimensions match the requested image size.
            # Note: Numpy array shape is (y,x), but the sensor is set with (x,y)
            # hence the need to compare index 0 with index 1.
            assert arr.shape[0] == size[1]
