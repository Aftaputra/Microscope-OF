from __future__ import annotations
import logging
import importlib.resources
import os.path
from fastapi import Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from labthings_fastapi.thing_server import ThingServer
from labthings_sangaboard import SangaboardThing
from labthings_picamera2.thing import StreamingPiCamera2

from .things.autofocus import AutofocusThing
from .things.camera_stage_mapping import CameraStageMapper
from .things.system_control import SystemControlThing
from .things.settings_manager import SettingsManager
from .serve_static_files import add_static_files
import openflexure_microscope_server

logging.basicConfig(level=logging.INFO)

thing_server = ThingServer()
thing_server.add_thing(StreamingPiCamera2(), "/camera/")
thing_server.add_thing(SangaboardThing(), "/stage/")
thing_server.add_thing(AutofocusThing(), "/autofocus/")
thing_server.add_thing(CameraStageMapper(), "/camera_stage_mapping/")
thing_server.add_thing(SystemControlThing(), "/system_control/")
thing_server.add_thing(SettingsManager(), "/settings/")
try:
    add_static_files(thing_server.app)
except RuntimeError:
    print("Failed to add static files - you will have to do without them!")


app = thing_server.app

# TODO: update openflexure connect to make this unnecessary!!
# The endpoints below fool OpenFlexure Connect into thinking we are a
# v2 microscope, so we show up correctly.
# This is necessary until Connect is rebuilt.
@app.get("/routes")
def routes_stub() -> dict[str, dict]:
    fake_routes = [
        "/api/v2/",
        "/api/v2/streams/snapshot",
    ]
    return {url: {"url": url, "methods": ["GET"]} for url in fake_routes}

class JPEGResponse(Response):
    media_type = "image/jpeg"

@app.get("/api/v2/streams/snapshot")
@app.head("/api/v2/streams/snapshot")
async def thumbnail() -> JPEGResponse:
    blob = await thing_server.things["/camera/"].lores_mjpeg_stream.grab_frame()
    return JPEGResponse(blob)