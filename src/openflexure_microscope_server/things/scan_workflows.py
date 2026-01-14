from typing import Mapping, Optional

import labthings_fastapi as lt

from openflexure_microscope_server.scan_planners import ScanPlanner, SmartSpiral
from openflexure_microscope_server.things.autofocus import AutofocusThing
from openflexure_microscope_server.things.background_detect import (
    BackgroundDetectAlgorithm,
    ChannelDeviationLUV,
)


class ScanWorkflow(lt.Thing):
    """A base class for all Scanworkflows.

    Scan workflows set the behaviour of a scan, inclduing the background detection,
    scan planning, aquisition routine.
    """

    _detector: Optional[BackgroundDetectAlgorithm | Mapping[str, BackgroundDetectAlgorithm]] = lt.thing_slot()
    _planner_cls: type[ScanPlanner]


    @lt.property
    def ready(self) -> bool:
        """Whether this scanworkflow is ready to start."""
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a ready property."
        )

    def pre_scan_routine(self) -> None:
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a pre-scan routine."
        )

class HistoScanWorkflow(ScanWorkflow):
    _detector: ChannelDeviationLUV = lt.thing_slot()
    _planner_cls: type[ScanPlanner] = SmartSpiral
    _autofocus: AutofocusThing = lt.thing_slot()

    autofocus_dz: int = lt.setting(default=1000)
    """The z distance to perform an autofocus in steps."""

    @lt.property
    def ready(self) -> bool:
        """Whether this scanworkflow is ready to start."""
        return self._detector.ready

    def pre_scan_routine(self) -> None:
        self._autofocus.looping_autofocus(dz=self.autofocus_dz, start="centre")
