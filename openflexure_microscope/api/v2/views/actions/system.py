from labthings.server.view import View
import subprocess
import os
from sys import platform

from labthings.server.decorators import (
    ThingAction,
    doc_response,
)


def is_raspberrypi(raise_on_errors=False):
    """
    Checks if Raspberry Pi.
    """
    # I mean, if it works, it works...
    return os.path.exists("/usr/bin/raspi-config")


@ThingAction
class ShutdownAPI(View):
    """
    Attempt to shutdown the device 
    """

    @doc_response(201)
    def post(self):
        """
        Attempt to shutdown the device
        """
        subprocess.Popen(["sudo", "shutdown", "-h", "now"])

        return "{}", 201


@ThingAction
class RebootAPI(View):
    """
    Attempt to reboot the device 
    """

    @doc_response(201)
    def post(self):
        """
        Attempt to reboot the device
        """
        subprocess.Popen(["sudo", "shutdown", "-r", "now"])

        return "{}", 201
