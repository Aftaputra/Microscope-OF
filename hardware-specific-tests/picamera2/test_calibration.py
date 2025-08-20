"""Test data collection from the Raspberry Picamera."""

import tempfile

from fastapi.testclient import TestClient
from pytest import fixture

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera.picamera import StreamingPiCamera2


@fixture()
def picamera_thing() -> StreamingPiCamera2:
    """Return a StreamingPiCamera2 Thing.

    This is the Thing that the fixture client uses. It can be used to probe the
    Thing directly to check actions had the expected response.
    """
    return StreamingPiCamera2()


@fixture()
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
    # Missing algorithm returns None
    assert picamera_thing.get_tuning_algo("foo") is None
    # Real algorithm is a dict and contains expected keys
    assert isinstance(picamera_thing.get_tuning_algo("rpi.geq"), dict)
    assert "offset" in picamera_thing.get_tuning_algo("rpi.geq")

    # Set the tuning to None as it is technically optional. And check this
    # is handled gracefully.
    try:
        picamera_thing.tuning = None
    except lt.exceptions.NotConnectedToServerError:
        # Labthings will complain that it is not connected to a server
        pass
    # Check it is set to None.
    assert picamera_thing.tuning is None
    assert picamera_thing.get_tuning_algo("rpi.geq") is None


def test_calibration(picamera_thing, client):
    """Check that full auto calibrate completes without an exception."""
    tuning = picamera_thing.tuning
    default_tuning = picamera_thing.default_tuning
    # Tuning should start the same as the server is loading with no settings.
    assert default_tuning == tuning
    # After calibration they should be different
    client.full_auto_calibrate()
    assert default_tuning != tuning
