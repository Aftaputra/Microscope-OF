from typing import Mapping, Optional

from pydantic import BaseModel

import labthings_fastapi as lt

from openflexure_microscope_server.scan_directories import StitchingData
from openflexure_microscope_server.scan_planners import ScanPlanner, SmartSpiral
from openflexure_microscope_server.stitching import STITCHING_RESOLUTION
from openflexure_microscope_server.things.autofocus import (
    MAX_TEST_IMAGE_COUNT,
    MIN_TEST_IMAGE_COUNT,
    AutofocusThing,
    SmartStackParams,
)
from openflexure_microscope_server.things.background_detect import (
    ChannelDeviationLUV,
)
from openflexure_microscope_server.things.camera_stage_mapping import CameraStageMapper


class ScanWorkflow(lt.Thing):
    """A base class for all Scanworkflows.

    Scan workflows set the behaviour of a scan, inclduing the background detection,
    scan planning, aquisition routine.
    """

    # All workdlows must have a set class for scan planning
    _planner_cls: type[ScanPlanner]

    # All workflows set a save resolution
    save_resolution: tuple[int, int] = lt.setting(default=(1640, 1232))
    """A tuple of the image resolution to capture."""

    def check_before_start(self, scan_name: str) -> None:
        """Check before the scan starts. Throw an error if the scan shouldn't start.

        The scan_name is passed to this function to enable workflows to validate the
        scan name if needed.
        """
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a check_before_start."
        )

    @lt.property
    def ready(self) -> bool:
        """Whether this scanworkflow is ready to start."""
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a ready property."
        )

    # TODO should be a model
    def all_settings(self, images_dir: str) -> tuple[dict, Optional[StitchingData]]:
        """Return the scan settings and the stitching settings.

        - The specific settings for this scan workflow are returned as a dict.
        - Stitiching settings are returned either as a StitchingData object or None
            is returned if it is not possible to stitch the scan.
        """
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a `all_settings`. method."
        )

    def pre_scan_routine(self, settings: dict) -> None:
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a pre-scan routine."
        )

    def new_scan_planner(self, settings: dict, position: Mapping[str, int]) -> None:
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a ``new_scan_planner`` method."
        )

    def aquisition_routine(
        self, settings: dict, xyz_pos: tuple[int, int, int]
    ) -> tuple[bool, Optional[int]]:
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement an aquisition routine"
        )


class HistoScanSettingsModel(BaseModel):
    """The settings including needed for running a HistoScan.

    This includes settings caluclated when starting. This will be serialised in
    ScanData.
    """

    overlap: float
    max_dist: int
    dx: int
    dy: int
    skip_background: bool
    smart_stack_prarams: SmartStackParams


class HistoScanWorkflow(ScanWorkflow):
    # Thing Slots
    _background_detector: ChannelDeviationLUV = lt.thing_slot()
    _csm: CameraStageMapper = lt.thing_slot()
    _planner_cls: type[ScanPlanner] = SmartSpiral
    _autofocus: AutofocusThing = lt.thing_slot()

    # Scan settings

    skip_background: bool = lt.setting(default=True)
    """Whether to detect and skip empty fields of view.

    This uses the settings from the ``BackgroundDetectThing``.
    """

    autofocus_dz: int = lt.setting(default=1000)
    """The z distance to perform an autofocus in steps."""

    max_range: int = lt.setting(default=45000)
    """The maximum distance in steps from the centre of the scan."""

    overlap: float = lt.setting(default=0.45)
    """The fraction (0-1) that adjacent images should overlap in x or y."""

    # Stacking settings

    stack_images_to_save: int = lt.setting(default=1)
    """The number of images to save in a stack.

    Defaults to 1 unless you need to see either side of focus
    """

    stack_min_images_to_test: int = lt.setting(default=9)
    """The minimum number of images to capture in a stack.

    This many images are captures and tested for focus, if the focus is not central
    enough more images may be captured. After new images are captured the number sets
    the number of images used for checking if focus is central.

    Defaults to 9 which balances reliability and speed.
    """

    stack_dz: int = lt.setting(default=50)
    """Distance in steps between images in a z-stack.

    Suggested values:

    * 50 for 60-100x
    * 100 for 40x
    * 200 for 20x
    """

    # noqa, scan_name is unused but is needed for equivalence with other workflows.
    def check_before_start(self, scan_name: str) -> None:  # noqa: ARG002
        """Before starting a scan, check that background and camera-stage-mapping are set.

        Raise error if:
          - background is to be skipped but is not set
          - camera stage mapping is not set

        Raise warning if not using background detect that scan will go on until max steps reached
        """
        if self._csm.calibration_required:
            raise RuntimeError("Camera Stage Mapping is not calibrated.")

        if self.skip_background:
            if not self._background_detector.ready:
                raise RuntimeError(
                    "Background is not set: you need to calibrate background detection."
                )
        else:
            self.logger.warning(
                "This scan will run in a spiral from the starting point "
                f"until you cancel it, or until it has moved by {self.max_range} steps "
                "in every direction. Make sure you watch it run to stop it leaving "
                "the area of interest, or (worse) leading the microscope's range "
                "of motion."
            )

    @lt.property
    def ready(self) -> bool:
        """Whether this scanworkflow is ready to start."""
        if self._csm.calibration_required:
            return False
        if not self.skip_background:
            return True
        return self._background_detector.ready

    def all_settings(
        self, images_dir: str
    ) -> tuple[HistoScanSettingsModel, StitchingData]:
        stitching_settings = StitchingData(
            overlap=self.overlap,
            correlation_resize=STITCHING_RESOLUTION[0] / self.save_resolution[0],
        )

        dx, dy = self._calc_displacement_from_test_image(self.overlap)
        self.logger.info(
            f"Based on an overlap of {self.overlap}, the stage will make steps of "
            f"{dx}, {dy}"
        )

        autofocus_dz = self.autofocus_dz
        if autofocus_dz == 0:
            self.logger.info("Running scan without autofocus")
        elif autofocus_dz <= 200:
            self.logger.warning(
                f"Your autofocus range is {autofocus_dz} steps, which is too short to "
                "attempt to focus. Running without autofocus"
            )
            autofocus_dz = 0

        smart_stack_prarams = self.create_smart_stack_params(
            images_dir=images_dir,
            autofocus_dz=autofocus_dz,
            save_resolution=self.save_resolution,
        )

        scan_settings = HistoScanSettingsModel(
            overlap=self.overlap,
            max_dist=self.max_range,
            dx=dx,
            dy=dy,
            skip_background=self.skip_background,
            smart_stack_prarams=smart_stack_prarams,
        )
        autofocus_dz = (autofocus_dz,)

        return scan_settings, stitching_settings

    def _calc_displacement_from_overlap(self, overlap: float) -> tuple[int, int]:
        """Take a test image and use camera stage mapping to calculate x and y displacement.

        :param overlap: The desired overlap as a fraction of the image. i.e. 0.5 means
            that each image should overlap its nearest neighbour by 50%.

        :returns: (dx, dy) - the x and y displacements in steps
        """
        csm_image_res = [int(i) for i in self._csm.image_resolution]

        # Calculate displacements in image coordinates
        dx_img = csm_image_res[1] * (1 - overlap)
        dy_img = csm_image_res[0] * (1 - overlap)

        x_move_stage = self._csm.convert_image_to_stage_coordinates(x=dx_img, y=0)
        y_move_stage = self._csm.convert_image_to_stage_coordinates(x=0, y=dy_img)

        # Assume no rotation or skew and take only the aligned axis of vector.
        # Coerce to positive integer, but correct if x and y are flipped
        if abs(x_move_stage["x"]) > abs(x_move_stage["y"]):
            return x_move_stage["x"], y_move_stage["y"]
        # If not use the other stage axes
        return x_move_stage["y"], y_move_stage["x"]

    def create_smart_stack_params(
        self,
        images_dir: str,
        autofocus_dz: int,
        save_resolution: tuple[int, int],
    ) -> SmartStackParams:
        """Set up the parameters used for all stacks in a scan.

        :param images_dir: the folder to save all images
        :param autofocus_dz: the range to autofocus over if a stack fails
        :param save_resolution: The resolution to save the captures to disk with

        :returns: A StackSmartParams object with the required parameters.
        """
        # Coerce min_images_to_test parameter
        min_images_to_test = self.stack_min_images_to_test
        if min_images_to_test < MIN_TEST_IMAGE_COUNT:
            self.logger.warning(
                f"Cannot test only {min_images_to_test} image(s) as this will fail. "
                "Setting min images to test to lowest possible value of"
                f"{MIN_TEST_IMAGE_COUNT}."
            )
            min_images_to_test = MIN_TEST_IMAGE_COUNT
        elif min_images_to_test > MAX_TEST_IMAGE_COUNT:
            self.logger.warning(
                f"Testing {min_images_to_test} images will cause defocus. "
                "Setting min images to test to highest possible value of "
                f"{MAX_TEST_IMAGE_COUNT}."
            )
            min_images_to_test = MAX_TEST_IMAGE_COUNT
        elif min_images_to_test % 2 == 0:
            min_images_to_test += 1
            self.logger.warning(
                "Minimum number of images to test should be odd, setting to "
                f"{min_images_to_test}."
            )
        # Set the Thing property to the coerced value
        self.stack_min_images_to_test = min_images_to_test

        # Coerce the images to save parameter to be positive, odd, and less than
        # min_images_to_save
        images_to_save = self.stack_images_to_save
        if images_to_save <= 0:
            self.logger.warning(
                "At least 1 images must be saved. Setting images to save to 1."
            )
            images_to_save = 1
        elif images_to_save > min_images_to_test:
            self.logger.warning(
                f"Cannot save {images_to_save} images as this above the minimum "
                f"number to test. Setting images to save to {MAX_TEST_IMAGE_COUNT}."
            )
            images_to_save = min_images_to_test
        elif images_to_save % 2 == 0:
            images_to_save += 1
            self.logger.warning(
                f"Images to save should be odd, setting to {images_to_save}."
            )
        # Set the Thing property to the coerced value
        self.stack_images_to_save = images_to_save

        return SmartStackParams(
            stack_dz=self.stack_dz,
            images_to_save=self.stack_images_to_save,
            min_images_to_test=self.stack_min_images_to_test,
            autofocus_dz=autofocus_dz,
            images_dir=images_dir,
            save_resolution=save_resolution,
        )

    def pre_scan_routine(self, settings: HistoScanSettingsModel) -> None:
        self._autofocus.looping_autofocus(dz=settings.autofocus_dz, start="centre")

    def new_scan_planner(
        self, settings: HistoScanSettingsModel, position: Mapping[str, int]
    ) -> None:
        # The initial plan for the scan should be a single x,y position. All future
        # moves will be planned around this point. In future, route planner could
        # have multiple starting positions, each of which will be visited before the
        # scan can end.
        planner_settings = {
            "dx": settings.dx,
            "dy": settings.dy,
            "max_dist": settings.max_dist,
        }
        return self._planner_cls(
            initial_position=(position["x"], position["y"]),
            planner_settings=planner_settings,
        )

    def aquisition_routine(
        self, settings: HistoScanSettingsModel, xyz_pos: tuple[int, int, int]
    ) -> tuple[bool, Optional[int]]:
        """Perform aquisition routine. This is run at each scan location.

        :return: A tuple of whether an image was taken, and the z-position for focus.
            If failed to find focus, returns for the focus z-position.
        """
        # If skipping background, take an image to check if current field of view is background
        if settings.skip_background:
            capture_image, bg_message = self._cam.image_is_sample()

        if not capture_image:
            msg = f"Skipping {xyz_pos} as it is {bg_message}."
            self.logger.info(msg)
            return False, None

        save_on_failure = settings.skip_background

        focused, focused_height = self._autofocus.run_smart_stack(
            stack_parameters=settings.smart_stack_params,
            save_on_failure=save_on_failure,
        )
        # An image was captured if we are focussed or we are not skipping background.
        imaged = focused or save_on_failure

        # run_smart_stage always returns a focus height for the sharpest image even
        # if it failed to find a good focus. Set to None if not focussed.
        if not focused:
            focused_height = None

        return imaged, focused_height
