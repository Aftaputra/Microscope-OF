from openflexure_microscope.api.views import MicroscopeView

import subprocess
import io
from sys import platform


def is_raspberrypi(raise_on_errors=False):
    """
    Checks if Raspberry Pi.
    """
    try:
        with io.open('/proc/cpuinfo', 'r') as cpuinfo:
            found = False
            for line in cpuinfo:
                if line.startswith('Hardware'):
                    found = True
                    label, value = line.strip().split(':', 1)
                    value = value.strip()
                    if value not in (
                        'BCM2708',
                        'BCM2709',
                        'BCM2835',
                        'BCM2836'
                    ):
                        if raise_on_errors:
                            raise ValueError(
                                'This system does not appear to be a '
                                'Raspberry Pi.'
                            )
                        else:
                            return False
            if not found:
                if raise_on_errors:
                    raise ValueError(
                        'Unable to determine if this system is a Raspberry Pi.'
                    )
                else:
                    return False
    except IOError:
        if raise_on_errors:
            raise ValueError('Unable to open `/proc/cpuinfo`.')
        else:
            return False

    return True

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
