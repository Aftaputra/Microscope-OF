import time
import logging
import numpy as np
from contextlib import contextmanager

from openflexure_microscope.plugins import MicroscopePlugin
from openflexure_microscope.utilities import set_properties

from .focus_utils import sharpness_sum_lap2, JPEGSharpnessMonitor
from .api import MeasureSharpnessAPI, AutofocusAPI, FastAutofocusAPI


class AutofocusPlugin(MicroscopePlugin):
    """
    Basic autofocus plugin
    """

    api_views = {
        '/measure_sharpness': MeasureSharpnessAPI,
        '/autofocus': AutofocusAPI,
        '/fast_autofocus': FastAutofocusAPI,
    }

    ### SLOW AUTOFOCUS

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

            for _ in stage.scan_z(dz, return_to_start=False):
                positions.append(stage.position[2])
                time.sleep(settle)
                sharpnesses.append(self.measure_sharpness(metric_fn))

            newposition = positions[np.argmax(sharpnesses)]
            stage.focus_rel(newposition - stage.position[2])

        return positions, sharpnesses

    def measure_sharpness(self, metric_fn=sharpness_sum_lap2):
        """Measure the sharpness of the camera's current view."""
        return metric_fn(self.microscope.camera.array(use_video_port=True))

    ### FAST AUTOFOCUS

    #JPEGSharpnessMonitor = JPEGSharpnessMonitor # make the class available
    def sharpness_monitor(self):
        return JPEGSharpnessMonitor(self.microscope)

    @contextmanager
    def monitor_sharpness(self):
        m = self.sharpness_monitor()
        m.start()
        try:
            yield m
        finally:
            m.stop()

    def move_and_find_focus(self, dz):
        """Make a relative Z move and return the peak sharpness position"""
        with self.monitor_sharpness() as m:
            m.focus_rel(dz)
            return m.sharpest_z_on_move(0)


    def fast_autofocus(self, dz=2000, backlash=None):
        """Perform a down-up-down-up autofocus"""
        with self.monitor_sharpness() as m:
            i, z = m.focus_rel(-dz/2)
            i, z = m.focus_rel(dz)
            fz = m.sharpest_z_on_move(i)
            if backlash is None:
                i, z = m.focus_rel(-dz) # move all the way to the start so it's consistent
            else:
                i, z = m.focus_rel(fz - z - backlash)
            m.focus_rel(fz - z)
            return m.data_dict()