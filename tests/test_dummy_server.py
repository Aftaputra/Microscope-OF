import tempfile

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from labthings_fastapi.client import ThingClient

from openflexure_microscope_server.server import ThingServer
from openflexure_microscope_server.things.camera.simulation import SimulatedCamera
from openflexure_microscope_server.things.stage.dummy import DummyStage
from openflexure_microscope_server.things.autofocus import AutofocusThing

temp_folder = tempfile.TemporaryDirectory()
server = ThingServer(temp_folder.name)
server.add_thing(SimulatedCamera(), "/camera/")
server.add_thing(DummyStage(), "/stage/")
server.add_thing(AutofocusThing(), "/autofocus/")

def test_autofocus():
    with TestClient(server.app) as client:
        autofocus = ThingClient.from_url("/autofocus/", client)
        _ = autofocus.fast_autofocus()
