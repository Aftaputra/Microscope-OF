"""Use the Simulation camera to test base camera functionality."""

import tempfile
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
import numpy as np
from PIL import Image

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera.simulation import SimulatedCamera


@contextmanager
def camera_server(camera: SimulatedCamera) -> lt.ThingClient:
    """Add the camera to a ThingServer and start a TestClient application.

    The test client application is needed for the camera to have a blocking portal.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        server = lt.ThingServer(settings_folder=tmpdir)
        server.add_thing(camera, "/camera/")
        with TestClient(server.app):
            yield server


def test_handle_broken_frame():
    """Monkey patch the the mjpeg steam so 1 in 5 frames are broken, then test operation.

    This simulates the very occasional broken frames that can occur when grabbing
    directly from the MJPEG stream.
    """
    camera = SimulatedCamera()

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
    with camera_server(camera):
        portal = lt.get_blocking_portal(camera)

        # Check that this does cause broken frames.
        # The noqa is because we don't know exactly when the error is thrown so we
        # can't have a single simple statement in the pytest raises.
        with pytest.raises(  # noqa PT012
            OSError, match="broken data stream when reading image file"
        ):
            for _i in range(15):
                jpeg = camera.grab_jpeg(portal)
                np.asarray(Image.open(jpeg.open()))

        # Check that grab_as_array handles the broken frames and completes without
        # the same error.
        for _i in range(15):
            array = camera.grab_as_array(portal)
            assert isinstance(array, np.ndarray)
