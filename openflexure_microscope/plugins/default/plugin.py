import time
import numpy as np

from openflexure_microscope.plugins import MicroscopePlugin
from openflexure_microscope.utilities import set_properties

from .focus_utils import sharpness_sum_lap2
from .api import IdentifyAPI, MeasureSharpnessAPI, AutofocusAPI


class Plugin(MicroscopePlugin):
    """
    A set of default plugins
    """

    api_views = {
        '/identify': IdentifyAPI,
        '/measure_sharpness': MeasureSharpnessAPI,
        '/autofocus': AutofocusAPI,
    }

    def identify(self):
        """
        Demonstrate access to Microscope.camera, and Microscope.stage
        """

        response = "My parent camera is {}, and my parent stage is {}.".format(self.microscope.camera, self.microscope.stage)
        return response

    def autofocus(self, dz, settle=0.5, metric_fn=sharpness_sum_lap2):
        """Perform a simple autofocus routine.
        The stage is moved to z positions (relative to current position) in dz,
        and at each position an image is captured and the sharpness function 
        evaulated.  We then move back to the position where the sharpness was
        highest.  No interpolation is performed.
        dz is assumed to be in ascending order (starting at -ve values)
        """
        camera = self.microscope.camera
        stage = self.microscope.stage

        with set_properties(stage, backlash=256), stage.lock, camera.lock:
            sharpnesses = []
            positions = []
            camera.annotate_text = ""

            for i in stage.scan_z(dz, return_to_start=False):
                positions.append(stage.position[2])
                time.sleep(settle)
                sharpnesses.append(self.measure_sharpness(metric_fn))

            newposition = positions[np.argmax(sharpnesses)]
            stage.focus_rel(newposition - stage.position[2])

        return positions, sharpnesses

    def measure_sharpness(self, metric_fn=sharpness_sum_lap2):
        """Measure the sharpness of the camera's current view."""
        return metric_fn(self.microscope.camera.array(use_video_port=True, resize=(640,480)))
