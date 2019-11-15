from openflexure_microscope.api.views import MicroscopeView

from flask import jsonify

import subprocess
import logging


# TODO: Make robust against different host OS
class ShutdownAPI(MicroscopeView):
    def post(self):
        """
        Attempt to shutdown the device

        .. :quickref: Actions; Shutdown

        """
        subprocess.Popen(['shutdown', '-h', 'now'])

        return '', 202


class RebootAPI(MicroscopeView):
    def post(self):
        """
        Attempt to shutdown the device

        .. :quickref: Actions; Shutdown

        """
        subprocess.Popen(['sudo', 'shutdown', '-r', 'now'])

        return '', 202
