from openflexure_stage import OpenFlexureStage

from openflexure_microscope.lock import StrictLock

# TODO: Implement lock on movement
class Stage(OpenFlexureStage):
    def __init__(self, *args, **kwargs):
        self.lock = StrictLock(timeout=2)  #: Strict lock controlling thread access to camera hardware

        OpenFlexureStage.__init__(self, *args, **kwargs)
    
    def _move_rel_nobacklash(self, *args, **kwargs):
        """
        Overrides `OpenFlexureStage._move_rel_nobacklash` to acquire lock first.
        """
        with self.lock:
            OpenFlexureStage._move_rel_nobacklash(self, *args, **kwargs)