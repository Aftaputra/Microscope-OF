"""Test the functionality specific to the simulated camera."""

import pytest

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


def test_simulation_cam_calibration(test_env):
    """Test that the simulated camera can be calibrated and reports calibration correctly."""
    camera = test_env.get_thing_by_type(SimulatedCamera)
    assert camera.calibration_required
    camera.full_auto_calibrate()
    assert not camera.calibration_required
    assert camera.background_detector_status.ready
