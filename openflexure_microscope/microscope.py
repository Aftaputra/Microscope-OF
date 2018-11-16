# -*- coding: utf-8 -*-
"""
Defines a microscope object, binding a camera and stage with basic functionality.
"""

import numpy as np

from openflexure_stage import OpenFlexureStage
from .camera.pi import StreamingCamera


class Microscope(object):
    """
    A basic microscope object.

    The camera and stage should already be initialised, and passed as arguments.

    Args:
        camera (:py:class:`openflexure_microscope.camera.pi.StreamingCamera`): camera object
        microscope (:py:class:`openflexure_stage.stage.OpenFlexureStage`): stage object
    """
    def __init__(self, camera: StreamingCamera, stage: OpenFlexureStage):
        print("Assigning camera")
        self.camera = camera  #: :py:class:`openflexure_microscope.camera.pi.StreamingCamera`: Picamera object
        print("Assigning stage")
        self.stage = stage  #: :py:class:`openflexure_stage.stage.OpenFlexureStage`: OpenFlexure stage object
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

    # Create unified state
    @property
    def state(self):
        """Dictionary of the basic microscope state.

        Return:
            dict: Dictionary containing position data, and :py:attr:`openflexure_microscope.camera.base.BaseCamera.state`
        """
        state = {}

        # Add stage position
        position = self.stage.position
        state['position'] = {
            'x': position[0],
            'y': position[1],
            'z': position[2],
        }

        # Add camera state
        state.update(self.camera.state)

        return state
