from openflexure_microscope.api.views import MicroscopeView

import subprocess


class ShutdownAPI(MicroscopeView):
    """
    Attempt to shutdown the device 
    """

    def post(self):
        """
        Attempt to shutdown the device

        .. :quickref: Actions; Shutdown

        """
        subprocess.Popen(["shutdown", "-h", "now"])

        return "{}", 201


class RebootAPI(MicroscopeView):
    """
    Attempt to reboot the device 
    """

    def post(self):
        """
        Attempt to shutdown the device

        .. :quickref: Actions; Shutdown

        """
        subprocess.Popen(["shutdown", "-r", "now"])

        return "{}", 201
