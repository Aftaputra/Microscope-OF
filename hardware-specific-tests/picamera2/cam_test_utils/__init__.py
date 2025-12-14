"""Utilities to help with testing the camera."""

import tempfile
from contextlib import contextmanager
from typing import Optional

from fastapi.testclient import TestClient

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera.picamera import StreamingPiCamera2


@contextmanager
def camera_test_client(
    cam: Optional[StreamingPiCamera2] = None, settings_folder: Optional[str] = None
):
    """Yield a camera ThingClient on a camera server.

    This is a context manager, not a pytest fixture, as it needs to be created
    multiple times in some tests.

    :param cam: The camera Thing to be used. If not supplied a new one will be created.
    :param settings_folder: The settings folder for the camera, if none is supplied, new
        temporary directory will be used as the settings folder.
    """
    if cam is None:
        cam = StreamingPiCamera2()
    # Create a temp dir, if the setting folder is set it isn't really needed
    # but doesn't add much overhead.
    with tempfile.TemporaryDirectory() as tmpdir:
        if settings_folder is None:
            settings_folder = tmpdir
        server = lt.ThingServer(settings_folder=settings_folder)
        server.add_thing(cam, "camera")

        with TestClient(server.app) as test_client:
            client = lt.ThingClient.from_url("camera", client=test_client)
            yield client
    del server
    del cam
