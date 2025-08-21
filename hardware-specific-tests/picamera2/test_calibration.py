"""Test data collection from the Raspberry Picamera."""

import tempfile
from copy import deepcopy

from fastapi.testclient import TestClient
import pytest

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera.picamera import (
    StreamingPiCamera2,
    MissingCalibrationError,
)


@pytest.fixture()
def picamera_thing() -> StreamingPiCamera2:
    """Return a StreamingPiCamera2 Thing.

    This is the Thing that the fixture client uses. It can be used to probe the
    Thing directly to check actions had the expected response.
    """
    return StreamingPiCamera2()


@pytest.fixture()
def client(picamera_thing) -> lt.ThingClient:
    """Initialise a test client for the StreamingPiCamera2 Thing.

    This fixture:

    * Sets up a ThingServer,
    * Registers a StreamingPiCamera2 instance at the "/camera/" endpoint
    * Provides a ThingClient for interacting with it during tests.
    """
    temp_folder = tempfile.TemporaryDirectory()
    server = lt.ThingServer(settings_folder=temp_folder.name)
    server.add_thing(picamera_thing, "/camera/")
    with TestClient(server.app) as test_client:
        client = lt.ThingClient.from_url("/camera/", client=test_client)
        yield client


def test_get_tuning_algo(picamera_thing):
    """Test that get_tuning algorithm retrieves tuning algorithms."""
    # Missing algorithm raises an error.
    with pytest.raises(MissingCalibrationError):
        picamera_thing.get_tuning_algo("foo")
    # Or returns None if explicitly told not to error.
    assert picamera_thing.get_tuning_algo("foo", raise_if_missing=False) is None

    # Real algorithm is a dict and contains expected keys
    assert isinstance(picamera_thing.get_tuning_algo("rpi.geq"), dict)
    assert "offset" in picamera_thing.get_tuning_algo("rpi.geq")

    # Set the tuning to None as it is technically optional. And check this
    # is handled gracefully. This needs to be done in a try block as LabThings
    # tries and fails to emit an event.
    try:
        picamera_thing.tuning = None
    except lt.exceptions.NotConnectedToServerError:
        # Labthings will complain that it is not connected to a server
        pass

    # Check it is set to None despite the above LabThings issue.
    assert picamera_thing.tuning is None

    # Raises an error as there is no tuning file set.
    with pytest.raises(MissingCalibrationError):
        picamera_thing.get_tuning_algo("rpi.geq")
    # Or returns None if explicitly told not to error.
    assert picamera_thing.get_tuning_algo("rpi.geq", raise_if_missing=False) is None


def test_calibration(picamera_thing, client):
    """Check that full auto calibrate completes and set the expected values."""
    # Save copy of default tuning file for end of test
    original_default = deepcopy(picamera_thing.default_tuning)
    # Tuning should start the same as the server is loading with no settings.
    assert picamera_thing.default_tuning == picamera_thing.tuning
    # lens_shading tables should be None when loaded on default tuning as it is
    # adaptive
    assert picamera_thing.lens_shading_tables is None
    # The background detector isn't ready as there is no background image.
    assert not picamera_thing.background_detector_status.ready

    # Run full auto calibrate
    client.full_auto_calibrate()

    # After calibration the tuning files should be different
    assert picamera_thing.default_tuning != picamera_thing.tuning
    # The default should be unchanged
    assert picamera_thing.default_tuning == original_default
    # Lens shading tables should no longer be None
    assert picamera_thing.lens_shading_tables is not None
    # There should be exactly one colour correction matrix
    # (no variations by colour temp)
    assert len(picamera_thing.get_tuning_algo("rpi.ccm")["ccms"]) == 1
    # Green equalisation offset should be set to maximum.
    assert picamera_thing.get_tuning_algo("rpi.geq")["offset"] == 65535
    assert picamera_thing.background_detector_status.ready
