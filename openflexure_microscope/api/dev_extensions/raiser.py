from labthings.server.extensions import BaseExtension
from labthings.server.view import ActionView

class RaiseException(ActionView):
    def post(self):
        raise Exception("The developer raised an exception")

raiser_extension_v2 = BaseExtension(
    "org.openflexure.dev.raiser",
    version="0.1.0",
    description="Actions to cause various traumatic events in the microscope, used for testing.",
)

raiser_extension_v2.add_view(RaiseException, "/raise")