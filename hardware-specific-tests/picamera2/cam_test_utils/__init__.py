"""Utilities to help with testing the camera."""

import tempfile
from contextlib import contextmanager
from typing import Optional

from fastapi.testclient import TestClient

import labthings_fastapi as lt


@contextmanager
def camera_test_client_and_server(settings_folder: Optional[str] = None):
    """Yield a camera ThingClient and the associated camera server.

    This is a context manager, not a pytest fixture, as it needs to be created
    multiple times in some tests.

    :param cam: The camera Thing to be used. If not supplied a new one will be created.
    :param settings_folder: The settings folder for the camera, if none is supplied, new
        temporary directory will be used as the settings folder.
    """
    # Create a temp dir, if the setting folder is set it isn't really needed
    # but doesn't add much overhead.
    with tempfile.TemporaryDirectory() as tmpdir:
        if settings_folder is None:
            settings_folder = tmpdir
        thing_conf = {
            "camera": "openflexure_microscope_server.things.camera.picamera:StreamingPiCamera2",
        }
        server = lt.ThingServer(things=thing_conf, settings_folder=settings_folder)

        with TestClient(server.app) as test_client:
            client = lt.ThingClient.from_url("/camera/", client=test_client)
            yield client, server
    del server


@contextmanager
def camera_test_client(settings_folder: Optional[str] = None):
    """Yield a camera ThingClient on a camera server.

    This is a context manager, not a pytest fixture, as it needs to be created
    multiple times in some tests.

    :param cam: The camera Thing to be used. If not supplied a new one will be created.
    :param settings_folder: The settings folder for the camera, if none is supplied, new
        temporary directory will be used as the settings folder.
    """
    with camera_test_client_and_server(
        settings_folder=settings_folder
    ) as client_and_server:
        yield client_and_server[0]
