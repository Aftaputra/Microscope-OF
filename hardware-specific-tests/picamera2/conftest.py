"""Shared fixtures for picamera tests."""

import pytest

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera.picamera import StreamingPiCamera2

from .cam_test_utils import camera_test_client


@pytest.fixture
def picamera_thing() -> StreamingPiCamera2:
    """Return a StreamingPiCamera2 Thing.

    This is the Thing that the fixture picamera_client uses. It can be used to probe
    the Thing directly to check actions had the expected response.
    """
    return StreamingPiCamera2()


@pytest.fixture
def picamera_client(picamera_thing) -> lt.ThingClient:
    """Initialise a test picamera_client for the StreamingPiCamera2 Thing.

    This fixture:

    * Sets up a ThingServer,
    * Registers a StreamingPiCamera2 instance at the "/camera/" endpoint
    * Provides a ThingClient for interacting with it during tests.
    """
    with camera_test_client(cam=picamera_thing) as picamera_client:
        yield picamera_client
