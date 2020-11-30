import os
import subprocess

from labthings.views import ActionView


def is_raspberrypi() -> bool:
    """
    Checks if Raspberry Pi.
    """
    # I mean, if it works, it works...
    return os.path.exists("/usr/bin/raspi-config")


class ShutdownAPI(ActionView):
    """
    Attempt to shutdown the device 
    """

    def post(self):
        """
        Attempt to shutdown the device
        """
        p = subprocess.Popen(
            ["sudo", "shutdown", "-h", "now"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        out, err = p.communicate()
        return {"out": out, "err": err}


class RebootAPI(ActionView):
    """
    Attempt to reboot the device 
    """

    def post(self):
        """
        Attempt to reboot the device
        """
        p = subprocess.Popen(
            ["sudo", "shutdown", "-r", "now"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        out, err = p.communicate()
        return {"out": out, "err": err}
