"""Use the Simulated camera to test base camera functionality.

For tests of functionality specific to the simulated camera see
test_simulated_camera.py and for testing the consistency of camera APIs see
test_cameras.py.
"""

import numpy as np
import pytest
from PIL import Image

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera.simulation import SimulatedCamera
from openflexure_microscope_server.things.stage.dummy import DummyStage

from ..shared_utils.lt_test_utils import LabThingsTestEnv


@pytest.fixture
def test_env() -> lt.ThingClient:
    """Yield a test environment with the Simulated Camera and Dummy Stage."""
    thing_conf = {"camera": SimulatedCamera, "stage": DummyStage}
    with LabThingsTestEnv(things=thing_conf) as env:
        yield env


def test_handle_broken_frame(test_env):
    """Monkey patch the the mjpeg steam so 1 in 5 frames are broken, then test operation.

    This simulates the very occasional broken frames that can occur when grabbing
    directly from the MJPEG stream.
    """
    camera = test_env.get_thing_by_type(SimulatedCamera)

    # Money patch the mjpeg_stream grab_frame to break 1 in 5 frames.
    frame_number = 0
    original_grabber = camera.mjpeg_stream.grab_frame

    async def flaky_grabber():
        """Break 1 in 5 frames."""
        # Use a non-local variable to know the frame count.
        nonlocal frame_number
        frame = await original_grabber()
        if frame_number % 5 == 2:
            # Make a weird broken frame
            frame = frame[:2000] + frame[:2000]
        frame_number += 1
        return frame

    camera.mjpeg_stream.grab_frame = flaky_grabber

    # Check that this does cause broken frames.
    # The noqa is because we don't know exactly when the error is thrown so we
    # can't have a single simple statement in the pytest raises.
    with pytest.raises(OSError, match="broken data stream when reading image file"):  # noqa PT012
        for _i in range(15):
            jpeg = camera.grab_jpeg()
            np.asarray(Image.open(jpeg.open()))

    # Check that grab_as_array handles the broken frames and completes without
    # the same error.
    for _i in range(15):
        array = camera.grab_as_array()
        assert isinstance(array, np.ndarray)
