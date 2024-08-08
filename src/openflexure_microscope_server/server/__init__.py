from __future__ import annotations

from labthings_fastapi.thing_server import ThingServer
from labthings_sangaboard import SangaboardThing
from labthings_picamera2.thing import StreamingPiCamera2

from ..things.autofocus import AutofocusThing
from ..things.camera_stage_mapping import CameraStageMapper
from ..things.system_control import SystemControlThing
from ..things.settings_manager import SettingsManager
from ..things.auto_recentre_stage import RecentringThing
from ..things.smart_scan import SmartScanThing, BackgroundDetectThing
from ..things.test import APITestThing
from .serve_static_files import add_static_files
from .legacy_api import add_v2_endpoints
from ..logging import configure_logging, retrieve_log

configure_logging()

thing_server = ThingServer()
thing_server.add_thing(StreamingPiCamera2(), "/camera/")
thing_server.add_thing(SangaboardThing(), "/stage/")
thing_server.add_thing(RecentringThing(), "/auto_recentre_stage/")
thing_server.add_thing(AutofocusThing(), "/autofocus/")
thing_server.add_thing(CameraStageMapper(), "/camera_stage_mapping/")
thing_server.add_thing(SystemControlThing(), "/system_control/")
thing_server.add_thing(SettingsManager(), "/settings/")
thing_server.add_thing(SmartScanThing("application/openflexure-stitching/.venv/bin/openflexure-stitch"), "/smart_scan/")
thing_server.add_thing(BackgroundDetectThing(), "/background_detect/")
thing_server.add_thing(APITestThing(), "/api_test/")
try:
    add_static_files(thing_server.app)
except RuntimeError:
    print("Failed to add static files - you will have to do without them!")

add_v2_endpoints(thing_server)  # Add the v2 endpoints for compatibility with OpenFlexure Connect

# Add an endpoint to get the log
thing_server.app.get("/log/")(retrieve_log)


app = thing_server.app

