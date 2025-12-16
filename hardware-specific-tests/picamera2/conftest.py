"""Shared fixtures for picamera tests."""

import pytest

import labthings_fastapi as lt

from .cam_test_utils import camera_test_client_and_server


@pytest.fixture
def picamera_client_and_server() -> lt.ThingClient:
    """Initialise a test picamera_client and server for the StreamingPiCamera2 Thing.

    This fixture:

    * Sets up a ThingServer,
    * Registers a StreamingPiCamera2 instance at the "camera" endpoint
    * Yields a ThingClient and the server for interacting with it during tests.
    * The picamera thing can be found at server.things["camera"]
    """
    with camera_test_client_and_server() as client_and_server:
        yield client_and_server


@pytest.fixture
def picamera_client(picamera_client_and_server) -> lt.ThingClient:
    """Initialise a test picamera_client for the StreamingPiCamera2 Thing.

    This fixture:

    * Sets up a ThingServer,
    * Registers a StreamingPiCamera2 instance at the "camera" endpoint
    * return a ThingClient for interacting with it during tests.
    """
    return picamera_client_and_server[0]
