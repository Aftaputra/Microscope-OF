"""Utilities to help with testing the camera."""

from typing import Optional
import tempfile

from contextlib import contextmanager

from fastapi.testclient import TestClient

from labthings_fastapi.server import ThingServer
from labthings_fastapi.client import ThingClient

from openflexure_microscope_server.things.camera.picamera import StreamingPiCamera2


@contextmanager
def camera_test_client(settings_folder: Optional[str] = None):
    """Yield a camera ThingClient on a camera server.

    This is a context manager not a pytest fixture as it needs to be created
    multiple times in some tests.
    """
    # Create a temp dir, if the setting folder is set it isn't really needed
    # but doesn't add much overhead.
    with tempfile.TemporaryDirectory() as tmpdir:
        if settings_folder is None:
            settings_folder = tmpdir
        cam = StreamingPiCamera2()
        server = ThingServer(settings_folder=settings_folder)
        server.add_thing(cam, "/camera/")

        with TestClient(server.app) as test_client:
            client = ThingClient.from_url("/camera/", client=test_client)
            yield client
    del server
    del cam
