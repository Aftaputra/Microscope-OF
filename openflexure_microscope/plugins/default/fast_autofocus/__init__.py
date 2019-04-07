import time
import numpy as np
import threading

from openflexure_microscope.plugins import MicroscopePlugin
from openflexure_microscope.utilities import set_properties
from openflexure_microscope.api.v1.views import MicroscopeViewPlugin
from openflexure_microscope.api.utilities import JsonPayload
from flask import request, jsonify, abort, current_app
import logging
from contextlib import contextmanager

class JPEGSharpnessMonitor():
    def __init__(self, microscope, timeout=60):
        self.microscope = microscope
        self.camera = microscope.camera
        self.stage = microscope.stage
        self.jpeg_sizes = []
        self.jpeg_times = []
        self.stage_positions = []
        self.stage_times = []
        self.stop_event = threading.Event()
        self.timeout = timeout
        self.keep_alive()
        self.background_thread = None
            
    def is_alive(self):
        if self.background_thread is None:
            return False
        else:
            return self.background_thread.is_alive()
            
    def should_stop(self):
        import time
        return time.time() - self.kept_alive > self.timeout
    
    def keep_alive(self):
        import time
        self.kept_alive = time.time()
    
    def start(self):
        "Start monitoring sharpness by looking at JPEG size"
        self.background_thread = threading.Thread(target=self._measure_jpegs)
        self.background_thread.start()
        return self
        
    def stop(self):
        "Stop the background thread"
        self.stop_event.set()
        self.background_thread.join()
        
    def _measure_jpegs(self):
        "Function that runs in a background thread to record sharpness"
        logging.info("Starting sharpness measurement in background thread")
        self.keep_alive()
        while not self.stop_event.is_set() and not self.should_stop():
            self.jpeg_sizes.append(self.jpeg_size())
            self.jpeg_times.append(time.time())
        if self.stop_event.is_set():
            logging.info("Cleanly stopped sharpness measurement in background thread")
        if self.should_stop():
            logging.info("Sharpness measurement timed out and has stopped")
   
    def jpeg_size(self):
        """Return the size of a frame from the MJPEG stream"""
        return len(self.camera.get_frame())


    def focus_rel(self, dz, backlash=False, **kwargs):
        self.keep_alive()
        self.stage_times.append(time.time())
        self.stage_positions.append(self.stage.position)
        self.stage.move_rel([0, 0, dz], backlash=backlash, **kwargs)
        self.stage_times.append(time.time())
        self.stage_positions.append(self.stage.position)
        i = len(self.stage_positions) - 2
        return i, self.stage_positions[-1][2]
        
    def move_data(self, istart, istop=None):
        "Extract sharpness as a function of (interpolated) z"
        global np, logging
        if istop is None:
            istop = istart + 2
        jpeg_times = np.array(self.jpeg_times)
        jpeg_sizes = np.array(self.jpeg_sizes)
        stage_times = np.array(self.stage_times)[istart:istop]
        stage_zs = np.array(self.stage_positions)[istart:istop, 2]
        start = np.argmax(jpeg_times > stage_times[0])
        stop = np.argmax(jpeg_times > stage_times[1])
        if stop < 1:
            stop = len(jpeg_times)
            logging.debug("changing stop to {}".format(stop))
        jpeg_times = jpeg_times[start:stop]
        jpeg_zs = np.interp(jpeg_times, stage_times, stage_zs)
        return jpeg_times, jpeg_zs, jpeg_sizes[start:stop]

    def sharpest_z_on_move(self, index):
        """Return the z position of the sharpest image on a given move"""
        jt, jz, js = self.move_data(index)
        return jz[np.argmax(js)]
    
    def data_dict(self):
        """Return the gathered data as a single convenient dictionary"""
        data = {}
        for k in ['jpeg_times', 'jpeg_sizes', 'stage_times', 'stage_positions']:
            data[k] = getattr(self, k)
        return data

class FastAutofocusAPI(MicroscopeViewPlugin):
    def post(self):
        payload = JsonPayload(request)
        
        # Figure out the parameters to use
        dz = payload.param("dz", default=2000, convert=int)
        backlash = payload.param("backlash", default=None, convert=int)
        if backlash < 0:
            backlash = None

        print("Running autofocus...")
        task = self.microscope.task.start(self.plugin.fast_autofocus, dz, backlash=backlash)

        # return a handle on the autofocus task
        return jsonify(task.state), 202

        

class Plugin(MicroscopePlugin):
    """
    Plugin to provide fast autofocus
    """
    JPEGSharpnessMonitor = JPEGSharpnessMonitor # make the class available
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


    api_views = {
            '/fast_autofocus': FastAutofocusAPI,
    }

