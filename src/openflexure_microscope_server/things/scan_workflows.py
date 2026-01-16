"""Scan workflows set different ways that smart scan can behave.

This module contains the base ``ScanWorkflow`` class that all workflows should subclass,
as well as specific workflows.
"""

from __future__ import annotations

from typing import (
    Generic,
    Mapping,
    Optional,
    TypeVar,
)

from pydantic import BaseModel

import labthings_fastapi as lt

from openflexure_microscope_server.scan_planners import ScanPlanner, SmartSpiral
from openflexure_microscope_server.stitching import (
    STITCHING_RESOLUTION,
    StitchingSettings,
)
from openflexure_microscope_server.things.autofocus import (
    MAX_TEST_IMAGE_COUNT,
    MIN_TEST_IMAGE_COUNT,
    AutofocusThing,
    SmartStackParams,
)
from openflexure_microscope_server.things.background_detect import (
    ChannelDeviationLUV,
)
from openflexure_microscope_server.things.camera import BaseCamera
from openflexure_microscope_server.things.camera_stage_mapping import CameraStageMapper
from openflexure_microscope_server.ui import PropertyControl, property_control_for

SettingModelType = TypeVar("SettingModelType", bound=BaseModel)


class ScanWorkflow(Generic[SettingModelType], lt.Thing):
    """A base class for all Scanworkflows.

    Scan workflows set the behaviour of a scan, including the background detection,
    scan planning, acquisition routine.
    """

    display_name: str = lt.property(default="Base Workflow", readonly=True)
    ui_blurb: str = lt.property(
        default="If you see this message, something is wrong.", readonly=True
    )

    _settings_model: type[SettingModelType]

    # All workflows must have a set class for scan planning
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

    def all_settings(
        self, images_dir: str
    ) -> tuple[SettingModelType, Optional[StitchingSettings]]:
        """Return the scan settings and the stitching settings.

        - The specific settings for this scan workflow are returned as a Base Model of
            the type set when defining the class.
        - Stitiching settings are returned either as a StitchingSettings object or None
            is returned if it is not possible to stitch the scan.
        """
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a `all_settings`. method."
        )

    def pre_scan_routine(self, settings: SettingModelType) -> None:
        """Overload to set the routine that happens before each scan."""
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a pre-scan routine."
        )

    def new_scan_planner(
        self, settings: SettingModelType, position: Mapping[str, int]
    ) -> ScanPlanner:
        """Return the a new scan planner object for a scan."""
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement a ``new_scan_planner`` method."
        )

    def acquisition_routine(
        self, settings: SettingModelType, xyz_pos: tuple[int, int, int]
    ) -> tuple[bool, Optional[int]]:
        """Overload to set the acquisition routine that happens at each scan site."""
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement an acquisition routine"
        )

    @lt.property
    def settings_ui(self) -> list[PropertyControl]:
        """A list of PropertyControl objects to create the settings in the scan tab."""
        raise NotImplementedError(
            "Each scan workflow must implement a settings_ui method."
        )


class HistoScanSettingsModel(BaseModel):
    """The settings for a scan with the HistoScanWorkflow.

    This includes settings calculated when starting. This will be held by smart scan
    during a scan and serialised to disk.
    """

    overlap: float
    max_dist: int
    dx: int
    dy: int
    skip_background: bool
    smart_stack_params: SmartStackParams


class HistoScanWorkflow(ScanWorkflow[HistoScanSettingsModel]):
    """A workflow optimised for scanning Histopathology samples.

    This workflow automatically plans its own path around a sample spiralling out from
    the centre position, scanning only where it detects sample.
    """

    display_name: str = lt.property(default="Histo Scan", readonly=True)
    ui_blurb: str = lt.property(
        default=(
            "This scan workflow is optimised for scanning H&E stained biopsies. It"
            "spirals out from the starting location, scanning only where it detects"
            "sample. It also works well for many other flat, well-featured samples."
        ),
        readonly=True,
    )

    _settings_model = HistoScanSettingsModel
    _planner_cls: type[ScanPlanner] = SmartSpiral
    # Thing Slots
    _background_detector: ChannelDeviationLUV = lt.thing_slot()
    _cam: BaseCamera = lt.thing_slot()
    _csm: CameraStageMapper = lt.thing_slot()
    _autofocus: AutofocusThing = lt.thing_slot()

    # Scan settings

    skip_background: bool = lt.setting(default=True)
    """Whether to detect and skip empty fields of view.

    This uses the settings from the ``BackgroundDetectThing``.
    """

    autofocus_dz: int = lt.setting(default=1000, ge=200, le=2000)
    """The z distance to perform an autofocus in steps.

    Must be greater than or equal to 200, and less than or equal to 2000.
    """

    max_range: int = lt.setting(default=45000)
    """The maximum distance in steps from the centre of the scan."""

    overlap: float = lt.setting(default=0.45, ge=0.1, le=0.7)
    """The fraction that adjacent images should overlap in x or y.

    This must be between 0.1 and 0.7.
    """

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

    # The noqa statement is because scan_name is unused but is needed for equivalence
    # with other workflows that may want to validate the scan name.
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
    ) -> tuple[HistoScanSettingsModel, StitchingSettings]:
        """Return the workflow and stitching settings.

        :param images_dir: The directory that images are to be written to.
        :return: A tuple containing the settings model for this workflow and the
            settings model for stitching.
        """
        stitching_settings = StitchingSettings(
            overlap=self.overlap,
            correlation_resize=STITCHING_RESOLUTION[0] / self.save_resolution[0],
        )

        dx, dy = self._calc_displacement_from_overlap(self.overlap)
        self.logger.info(
            f"Based on an overlap of {self.overlap}, the stage will make steps of "
            f"{dx}, {dy}"
        )

        smart_stack_params = self.create_smart_stack_params(
            images_dir=images_dir,
            autofocus_dz=self.autofocus_dz,
            save_resolution=self.save_resolution,
        )

        scan_settings = HistoScanSettingsModel(
            overlap=self.overlap,
            max_dist=self.max_range,
            dx=dx,
            dy=dy,
            skip_background=self.skip_background,
            smart_stack_params=smart_stack_params,
        )

        return scan_settings, stitching_settings

    def _calc_displacement_from_overlap(self, overlap: float) -> tuple[int, int]:
        """Take a test image and use camera stage mapping to calculate x and y displacement.

        :param overlap: The desired overlap as a fraction of the image. i.e. 0.5 means
            that each image should overlap its nearest neighbour by 50%.

        :returns: (dx, dy) - the x and y displacements in steps
        """
        csm_image_res = self._csm.image_resolution
        if csm_image_res is None:
            raise RuntimeError("CSM not set. Scan shouldn't have progresses this far.")

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
        """Autofocus before starting the scan.

        :param settings: The settings for this scan as a HistoScanSettingsModel
        """
        self._autofocus.looping_autofocus(
            dz=settings.smart_stack_params.autofocus_dz, start="centre"
        )

    def new_scan_planner(
        self, settings: HistoScanSettingsModel, position: Mapping[str, int]
    ) -> ScanPlanner:
        """Return a new scan planner object.

        :param settings: The settings for this scan as a HistoScanSettingsModel
        :param position: The starting position as a mapping of axes names to int.
        """
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

    def acquisition_routine(
        self, settings: HistoScanSettingsModel, xyz_pos: tuple[int, int, int]
    ) -> tuple[bool, Optional[int]]:
        """Perform acquisition routine. This is run at each scan location.

        :param settings: The settings for this scan as a HistoScanSettingsModel
        :param xyz_pos: The current position as a tuple or 3 ints.
        :return: A tuple of whether an image was taken, and the z-position for focus.
            If failed to find focus, returns for the focus z-position.
        """
        # If skipping background, take an image to check if current field of view is background
        if settings.skip_background:
            image_array = self._cam.grab_as_array(stream_name="lores")
            capture_image, bg_message = self._background_detector.image_is_sample(
                image_array
            )
            del image_array

        if not capture_image:
            msg = f"Skipping {xyz_pos} as it is {bg_message}."
            self.logger.info(msg)
            return False, None

        save_on_failure = settings.skip_background

        focus_height: Optional[int]
        focused, focus_height = self._autofocus.run_smart_stack(
            stack_parameters=settings.smart_stack_params,
            save_on_failure=save_on_failure,
        )
        # An image was captured if we are focussed or we are not skipping background.
        imaged = focused or save_on_failure

        # run_smart_stage always returns a focus height for the sharpest image even
        # if it failed to find a good focus. Set to None if not focussed.
        if not focused:
            focus_height = None

        return imaged, focus_height

    @lt.property
    def settings_ui(self) -> list[PropertyControl]:
        """A list of PropertyControl objects to create the settings in the scan tab."""
        return [
            property_control_for(self, "overlap", label="Image Overlap (0.1-0.7)"),
            property_control_for(
                self, "skip_background", label="Detect and Skip Empty Fields "
            ),
            property_control_for(
                self, "stack_images_to_save", label="Images in Stack to Save"
            ),
            property_control_for(
                self,
                "stack_min_images_to_test",
                label="Minimum number of images to test for focus",
            ),
            property_control_for(self, "stack_dz", label="Stack dz (steps)"),
            property_control_for(self, "autofocus_dz", label="Autofocus Range (steps)"),
            property_control_for(self, "max_range", label="Maximum Distance (steps)"),
        ]
