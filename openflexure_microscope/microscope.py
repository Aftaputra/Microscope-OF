# -*- coding: utf-8 -*-
import numpy as np

from openflexure_stage import OpenFlexureStage
from .camera.pi import StreamingCamera


class Microscope(object):
    def __init__(self, camera: StreamingCamera, stage: OpenFlexureStage):
        """Create the microscope object.  The camera and stage should already be initialised."""
        self.camera = camera
        self.stage = stage
        self.stage.backlash = np.zeros(3, dtype=np.int)

    def __enter__(self):
        """Create microscope on context enter."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close microscope on context exit."""
        self.close()

    def close(self):
        """Shut down the microscope hardware."""
        self.camera.close()
        self.stage.close()
