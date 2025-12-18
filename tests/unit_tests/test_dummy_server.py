"""Test the server without creating a full HTTP server and socket connection.

Rather than spinning up a full uvicorn webserver for each test these tests use
the FastAPI ``TestClient`` or directly communicate with the underlying
LabThings-FastAPI code. This increases speed of testing significantly.

For tests that require a full running server see the ``integration-tests``
directory in the root of the repository.
"""

import json

import numpy as np
import piexif
import pytest
from PIL import Image

from ..shared_utils.lt_test_utils import LabThingsTestEnv


@pytest.fixture
def test_env():
    """Yield a server with a very basic configuration."""
    thing_conf = {
        "camera": {
            "class": "openflexure_microscope_server.things.camera.simulation:SimulatedCamera",
            "kwargs": {
                "shape": (240, 320, 3),
                "canvas_shape": (1000, 1500, 3),
                "frame_interval": 0.01,
            },
        },
        "stage": {
            "class": "openflexure_microscope_server.things.stage.dummy:DummyStage",
            "kwargs": {"step_time": 0.000001},
        },
        "autofocus": "openflexure_microscope_server.things.autofocus:AutofocusThing",
        "camera_stage_mapping": "openflexure_microscope_server.things.camera_stage_mapping:CameraStageMapper",
    }
    with LabThingsTestEnv(things=thing_conf) as env:
        yield env


def test_autofocus(test_env):
    """Test Fast Autofocus can run doesn't raise an exception."""
    # Adjust the time for stage is 100 microseconds rather than 1 microsecond.
    test_env.get_thing_by_name("stage").step_time = 0.0001
    autofocus = test_env.get_thing_client("autofocus")
    _ = autofocus.fast_autofocus()


def test_grab_jpeg(test_env):
    """Check that grab_jpeg returns a blob that can be opened."""
    camera = test_env.get_thing_client("camera")
    blob = camera.grab_jpeg()
    _image = Image.open(blob.open())


def test_capture_jpeg_metadata(test_env):
    """Check that the position is encoded into the image metadata."""
    camera = test_env.get_thing_client("camera")
    blob = camera.capture_jpeg()
    image = Image.open(blob.open())
    exif_dict = piexif.load(image.info["exif"])
    encoded_metadata = exif_dict["Exif"][piexif.ExifIFD.UserComment]
    metadata = json.loads(encoded_metadata)
    assert "position" in metadata["stage"]


def test_stage(test_env):
    """Test moving th stage forwards and backwards."""
    stage = test_env.get_thing_client("stage")
    start = stage.position
    move = {"x": 1, "y": 2, "z": 3}
    stage.move_relative(**move)
    pos = stage.position
    for s, m, p in zip(start.values(), move.values(), pos.values(), strict=True):
        assert s + m == p
    stage.move_relative(**{k: -v for k, v in move.items()})
    pos = stage.position
    for s, p in zip(start.values(), pos.values(), strict=True):
        assert s == p


def test_capture_array(test_env):
    """Capture array from simulation and check the size is as expected."""
    camera = test_env.get_thing_client("camera")
    array = np.asarray(camera.capture_array())
    assert array.shape == (240, 320, 3)


def test_camera_stage_mapping_calibration(test_env):
    """Check that camera stage mapping can run without an exception."""
    camera = test_env.get_thing_client("camera")
    camera.settling_time = 0
    camera_stage_mapping = test_env.get_thing_client("camera_stage_mapping")
    camera_stage_mapping.calibrate_xy()
