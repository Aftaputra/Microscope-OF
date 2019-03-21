from openflexure_stage import OpenFlexureStage

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

        OpenFlexureStage.__init__(self, *args, **kwargs)

    
    def _move_rel_nobacklash(self, *args, **kwargs):
        """
        Overrides :py:function:`openflexure_stage.stage.OpenFlexureStage._move_rel_nobacklash` to acquire lock first.
        """
        if self._ser:
            with self.lock:
                OpenFlexureStage._move_rel_nobacklash(self, *args, **kwargs)
        else:
            logging.warning("Unable to move stage. Serial communication unavailable.")
