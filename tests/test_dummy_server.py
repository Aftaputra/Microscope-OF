import json
import tempfile

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from labthings_fastapi.client import ThingClient
from PIL import Image
import piexif

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

def test_grab_jpeg():
    with TestClient(server.app) as client:
        camera = ThingClient.from_url("/camera/", client)
        blob = camera.grab_jpeg()
        _image = Image.open(blob.open())

def test_capture_jpeg_metadata():
    with TestClient(server.app) as client:
        camera = ThingClient.from_url("/camera/", client)
        blob = camera.capture_jpeg()
        image = Image.open(blob.open())
        exif_dict = piexif.load(image.info["exif"])
        encoded_metadata = exif_dict["Exif"][piexif.ExifIFD.UserComment]
        metadata = json.loads(encoded_metadata)
        assert "position" in metadata["/stage/"]

def test_stage():
    with TestClient(server.app) as client:
        stage = ThingClient.from_url("/stage/", client)
        start = stage.position
        move = {"x": 1, "y": 2, "z": 3}
        stage.move_relative(**move)
        pos = stage.position
        for s, m, p in zip(start.values(), move.values(), pos.values()):
            assert s + m == p
        stage.move_relative(**{k: -v for k, v in move.items()})
        pos = stage.position
        for s, p in zip(start.values(), pos.values()):
            assert s == p
