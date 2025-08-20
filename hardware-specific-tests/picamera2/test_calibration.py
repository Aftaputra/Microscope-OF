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


def test_calibration(picamera_thing, client):
    """Check that full auto calibrate completes without an exception."""
    tuning = picamera_thing.tuning
    default_tuning = picamera_thing.default_tuning
    # Tuning should start the same as the server is loading with no settings.
    assert default_tuning == tuning
    # After calibration they should be different
    client.full_auto_calibrate()
    assert default_tuning != tuning
