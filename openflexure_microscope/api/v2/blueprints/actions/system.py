from openflexure_microscope.api.views import MicroscopeView

import subprocess


class ShutdownAPI(MicroscopeView):
    def post(self):
        """
        Attempt to shutdown the device

        .. :quickref: Actions; Shutdown

        """
        subprocess.Popen(["shutdown", "-h", "now"])

        return "{}", 201


class RebootAPI(MicroscopeView):
    def post(self):
        """
        Attempt to shutdown the device

        .. :quickref: Actions; Shutdown

        """
        subprocess.Popen(["sudo", "shutdown", "-r", "now"])

        return "{}", 201
