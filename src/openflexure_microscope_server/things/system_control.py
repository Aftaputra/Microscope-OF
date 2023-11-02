"""
OpenFlexure Microscope API extension for stage calibration

This file contains the HTTP API for camera/stage calibration. It
includes calibration functions that measure the relationship between
stage coordinates and camera coordinates, as well as functions that
move by a specified displacement in pixels, perform closed-loop moves,
and return the calibration data.

This module is only intended to be called from the OpenFlexure Microscope
server, and depends on that server and its underlying LabThings library.
"""
import subprocess
import os
from labthings_fastapi.thing import Thing
from labthings_fastapi.decorators import thing_action, thing_property
from pydantic import BaseModel

class CommandOutput(BaseModel):
    output: str
    error: str


class SystemControlThing(Thing):
    """
    Attempt to shutdown the device 
    """

    @thing_action
    def shutdown(self) -> CommandOutput:
        """
        Attempt to shutdown the device
        """
        p = subprocess.Popen(
            ["sudo", "shutdown", "-h", "now"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

        out, err = p.communicate()
        return CommandOutput(output=out, error=err)

    @thing_property
    def is_raspberrypi() -> bool:
        """
        Checks if we are running on a Raspberry Pi.
        """
        return os.path.exists("/usr/bin/raspi-config")
    
    @thing_action
    def reboot(self) -> CommandOutput:
        """Attempt to reboot the device"""
        p = subprocess.Popen(
            ["sudo", "shutdown", "-r", "now"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        out, err = p.communicate()
        return CommandOutput(output=out, error=err)
