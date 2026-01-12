"""Test the server without creating a full HTTP server and socket connection.

Rather than spinning up a full uvicorn webserver for each test these tests use
the FastAPI ``TestClient`` or directly communicate with the underlying
LabThings-FastAPI code. This increases speed of testing significantly.

For tests that require a full running server see the ``lifecycle_test``
directory in the tests directory.

This file used to be called test_dummy_server when it was in the unit_test suite, but
it has been moved as it artificaially inflated coverage.
"""

import json
import os

import numpy as np
import piexif
import pytest
from PIL import Image

import labthings_fastapi as lt

from ..shared_utils.lt_test_utils import LabThingsTestEnv

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(THIS_DIR))
SIM_CONFIG = os.path.join(REPO_ROOT, "ofm_config_simulation.json")


@pytest.fixture
def test_env():
    """Yield a server with a very basic configuration."""
    with open(SIM_CONFIG, "r", encoding="utf-8") as f_obj:
        config_dict = json.load(f_obj)
    with LabThingsTestEnv(things=config_dict["things"]) as env:
        yield env


def test_autofocus(test_env):
    """Test Fast Autofocus can run doesn't raise an exception."""
    stage = test_env.get_thing_client("stage")
    autofocus = test_env.get_thing_client("autofocus")
    assert stage.position["z"] == 0
    # Autofocus 5 times and check each ends within 500 steps
    for i in range(5):
        autofocus.fast_autofocus()
        assert abs(stage.position["z"]) < 500, f"Autofocus failed on iteration {i}"


def test_grab_jpeg(test_env):
    """Check that grab_jpeg returns a blob that can be opened."""
    camera = test_env.get_thing_client("camera")
    blob = camera.grab_jpeg()
    image = Image.open(blob.open())
    assert image.size == (820, 616)


def test_capture_jpeg_metadata(test_env):
    """Check that the position is encoded into the image metadata."""
    camera = test_env.get_thing_client("camera")
    blob = camera.capture_jpeg()
    image = Image.open(blob.open())
    exif_dict = piexif.load(image.info["exif"])
    encoded_metadata = exif_dict["Exif"][piexif.ExifIFD.UserComment]
    metadata = json.loads(encoded_metadata)
    assert "position" in metadata["stage"]
    assert metadata["stage"]["position"] == {"x": 0, "y": 0, "z": 0}
    assert image.size == (820, 616)


def test_stage(test_env):
    """Test moving the stage forwards and backwards."""
    stage = test_env.get_thing_client("stage")
    start = stage.position
    move = {"x": 1, "y": 2, "z": 3}
    move_back = {"x": -1, "y": -2, "z": -3}
    stage.move_relative(**move)
    pos = stage.position

    assert start["x"] + move["x"] == pos["x"]
    assert start["y"] + move["y"] == pos["y"]
    assert start["z"] + move["z"] == pos["z"]

    # Move back
    stage.move_relative(**move_back)
    pos = stage.position

    # Check nack at start.
    assert start["x"] == pos["x"]
    assert start["y"] == pos["y"]
    assert start["z"] == pos["z"]


def test_capture_array(test_env):
    """Capture array from simulation and check the size is as expected."""
    camera = test_env.get_thing_client("camera")
    array = np.asarray(camera.capture_array())
    assert array.shape == (616, 820, 3)


def test_camera_stage_mapping_calibration(test_env):
    """Check that camera stage mapping runs and returns the expected result."""
    camera = test_env.get_thing_client("camera")
    # Remove camera settling time for speed.
    camera.settling_time = 0
    csm = test_env.get_thing_client("camera_stage_mapping")
    stage = test_env.get_thing_client("stage")

    # Check it starts uncalibrated
    assert csm.calibration_required
    assert csm.image_to_stage_displacement_matrix is None
    assert csm.last_calibration is None
    # And therefore that actions error
    with pytest.raises(lt.exceptions.FailedToInvokeActionError):
        csm.move_in_image_coordinates(x=10)

    # Calibrate
    csm.calibrate_xy()

    assert not csm.calibration_required
    assert csm.image_to_stage_displacement_matrix is not None
    assert isinstance(csm.last_calibration, dict)
    # Check it returned home
    assert stage.position == {"x": 0, "y": 0, "z": 0}
    csm.move_in_image_coordinates(x=10, y=0)
    assert stage.position == {"x": -5, "y": 0, "z": 0}
    csm_matrix = csm.image_to_stage_displacement_matrix
    expected_matrix = [[0, 0.5], [-0.5, 0]]
    assert isinstance(csm_matrix, list)
    # Check CSM is as expected to an absolute tolerance of 1e-3
    assert np.allclose(csm_matrix, expected_matrix, atol=1e-3)
