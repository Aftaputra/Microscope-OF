"""Use the Simulation camera to test base camera functionality."""

import tempfile

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import labthings_fastapi as lt


@pytest.fixture
def camera_server() -> lt.ThingClient:
    """Add the camera to a ThingServer and start a TestClient application.

    The test client will be needed for the camera to run async frame generation code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        conf = {
            "camera": "openflexure_microscope_server.things.camera.simulation:SimulatedCamera",
            "stage": "openflexure_microscope_server.things.stage.dummy:DummyStage",
        }

        server = lt.ThingServer(things=conf, settings_folder=tmpdir)
        yield server


def test_handle_broken_frame(camera_server):
    """Monkey patch the the mjpeg steam so 1 in 5 frames are broken, then test operation.

    This simulates the very occasional broken frames that can occur when grabbing
    directly from the MJPEG stream.
    """
    camera = camera_server.things["camera"]

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

    with TestClient(camera_server.app):
        # Check that this does cause broken frames.
        # The noqa is because we don't know exactly when the error is thrown so we
        # can't have a single simple statement in the pytest raises.
        with pytest.raises(  # noqa PT012
            OSError, match="broken data stream when reading image file"
        ):
            for _i in range(15):
                jpeg = camera.grab_jpeg()
                np.asarray(Image.open(jpeg.open()))

        # Check that grab_as_array handles the broken frames and completes without
        # the same error.
        for _i in range(15):
            array = camera.grab_as_array()
            assert isinstance(array, np.ndarray)


def test_simulation_cam_calibration(camera_server):
    """Test that the simulated camera can be calibrated and reports calibration correctly."""
    camera = camera_server.things["camera"]
    with TestClient(camera_server.app):
        assert camera.calibration_required
        camera.full_auto_calibrate()
        assert not camera.calibration_required
        assert camera.background_detector_status.ready
