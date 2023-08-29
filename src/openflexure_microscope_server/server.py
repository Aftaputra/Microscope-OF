from __future__ import annotations
import logging
from labthings_fastapi.thing_server import ThingServer
from labthings_sangaboard import SangaboardThing
from labthings_picamera2.thing import StreamingPiCamera2

logging.basicConfig(level=logging.INFO)

thing_server = ThingServer()
camera = StreamingPiCamera2()
thing_server.add_thing(camera, "/camera")
stage = SangaboardThing()
thing_server.add_thing(stage, "/stage")

app = thing_server.app