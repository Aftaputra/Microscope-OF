import logging
import time

from labthings import fields
from labthings.extensions import BaseExtension
from labthings.views import ActionView


class RaiseException(ActionView):
    def post(self):
        raise Exception("The developer raised an exception")


class SleepFor(ActionView):
    schema = {"TimeAsleep": fields.Float()}
    args = {"time": fields.Float(description="Time to sleep, in seconds", example=0.5)}

    def post(self, args):
        sleep_time = args.get("time")
        logging.info("Going to sleep for {}...", sleep_time)
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
