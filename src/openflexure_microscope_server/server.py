from __future__ import annotations
import logging
import importlib.resources
import os.path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from labthings_fastapi.thing_server import ThingServer
from labthings_sangaboard import SangaboardThing
from labthings_picamera2.thing import StreamingPiCamera2

from .things.autofocus import AutofocusThing
from .things.camera_stage_mapping import CameraStageMapper
from .serve_static_files import add_static_files
import openflexure_microscope_server

logging.basicConfig(level=logging.INFO)

thing_server = ThingServer()
thing_server.add_thing(StreamingPiCamera2(), "/camera/")
thing_server.add_thing(SangaboardThing(), "/stage/")
thing_server.add_thing(AutofocusThing(), "/autofocus/")
thing_server.add_thing(CameraStageMapper(), "/camera_stage_mapping/")
try:
    add_static_files(thing_server.app)
except RuntimeError:
    print("Failed to add static files - you will have to do without them!")


app = thing_server.app