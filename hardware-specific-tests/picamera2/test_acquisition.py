"""Test data collection from the Raspberry Picamera."""

import tempfile

from fastapi.testclient import TestClient
from PIL import Image
import numpy as np
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


def test_jpeg_and_array(client):
    """Check that a jpeg grabbed from the stream is the same size as other captures.

    Compare it to an array capture and a jpeg capture.
    """
    # Grab a jpeg from the stream
    blob = client.grab_jpeg()
    mjpeg_frame = Image.open(blob.open())
    assert mjpeg_frame

    # Capture a jpeg
    blob = client.capture_jpeg(resolution="main")
    jpeg_capture = Image.open(blob.open())
    assert jpeg_capture

    # Capture an array
    arrlist = client.capture_array(stream_name="main")
    array_main = np.array(arrlist)

    # Verify image sizes are the same
    assert mjpeg_frame.size == jpeg_capture.size
    assert array_main.shape[1::-1] == jpeg_capture.size
