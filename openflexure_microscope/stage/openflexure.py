from openflexure_stage import OpenFlexureStage

from openflexure_microscope.lock import StrictLock

# TODO: Implement lock on movement
class Stage(OpenFlexureStage):
    def __init__(self, *args, **kwargs):
        self.lock = StrictLock(timeout=2)  #: Strict lock controlling thread access to camera hardware

        OpenFlexureStage.__init__(self, *args, **kwargs)