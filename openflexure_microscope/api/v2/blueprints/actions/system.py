from openflexure_microscope.api.views import MicroscopeView

import subprocess
import os
from sys import platform


def is_raspberrypi(raise_on_errors=False):
    """
    Checks if Raspberry Pi.
    """
    # I mean, if it works, it works...
    return os.path.exists("/usr/bin/raspi-config")


class ShutdownAPI(MicroscopeView):
    """
    Attempt to shutdown the device 
    """

    def post(self):
        """
        Attempt to shutdown the device

        .. :quickref: Actions; Shutdown

        """
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])

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
        subprocess.Popen(["sudo", "shutdown", "-r", "now"])

        return "{}", 201
