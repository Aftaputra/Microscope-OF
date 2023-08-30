from __future__ import annotations
import logging
from labthings_fastapi.thing_server import ThingServer
from labthings_sangaboard import SangaboardThing
from labthings_picamera2.thing import StreamingPiCamera2

from .things.autofocus import AutofocusThing

logging.basicConfig(level=logging.INFO)

thing_server = ThingServer()
thing_server.add_thing(StreamingPiCamera2(), "/camera")
thing_server.add_thing(SangaboardThing(), "/stage")
thing_server.add_thing(AutofocusThing(), "/autofocus")

app = thing_server.app