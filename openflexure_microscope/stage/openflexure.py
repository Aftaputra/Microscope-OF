from openflexure_stage import OpenFlexureStage
from serial import SerialException

from openflexure_microscope.lock import StrictLock

import logging

# TODO: Implement lock on movement
class Stage(OpenFlexureStage):
    def __init__(self, *args, **kwargs):
        """
        Subclass of :py:class:`openflexure_stage.stage.OpenFlexureStage`, 
        adding an instance of :py:class:`openflexure_microscope.lock.StrictLock` to regulate access.
        """
        self.lock = StrictLock(timeout=2)  #: :py:class:`openflexure_microscope.lock.StrictLock`: Strict lock controlling thread access to camera hardware
        
        try:
            OpenFlexureStage.__init__(self, *args, **kwargs)
        except SerialException as e:
            logging.error("No stage found. Aborting stage.")
            logging.warning("Stage lock can be acquired, but any stage methods will fail and raise exceptions.")
    
    def _move_rel_nobacklash(self, *args, **kwargs):
        """
        Overrides :py:function:`openflexure_stage.stage.OpenFlexureStage._move_rel_nobacklash` to acquire lock first.
        """
        with self.lock:
            OpenFlexureStage._move_rel_nobacklash(self, *args, **kwargs)