from labthings.server.extensions import BaseExtension
from labthings.server.view import ActionView

from labthings.server import fields
from labthings.server.decorators import use_args, marshal_with

import logging
import time

class RaiseException(ActionView):
    def post(self):
        raise Exception("The developer raised an exception")

class SleepFor(ActionView):
    @marshal_with({
        "TimeAsleep": fields.Float()
    })
    @use_args({
        "time": fields.Float(description="Time to sleep, in seconds", example=0.5)
    })
    def post(self, args):
        sleep_time = args.get("time")
        logging.info(f"Going to sleep for {sleep_time}...")
        start = time.time()
        time.sleep(sleep_time)
        end = time.time()
        logging.info("Waking up!")
        return {"TimeAsleep": (end - start)}

devtools_extension_v2 = BaseExtension(
    "org.openflexure.dev.tools",
    version="0.1.0",
    description="Actions to cause various traumatic events in the microscope, used for testing.",
)

devtools_extension_v2.add_view(RaiseException, "/raise")
devtools_extension_v2.add_view(SleepFor, "/sleep")