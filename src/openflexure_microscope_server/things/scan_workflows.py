"""Scan workflows set different ways that smart scan can behave.

This module contains the base ``ScanWorkflow`` class that all workflows should subclass,
as well as specific workflows.
"""

from __future__ import annotations

import os
from typing import (
    Generic,
    Literal,
    Mapping,
    Optional,
    TypeVar,
)

from pydantic import BaseModel

import labthings_fastapi as lt

from openflexure_microscope_server.scan_planners import (
    RegularGridPlanner,
    ScanPlanner,
    SmartSpiral,
)
from openflexure_microscope_server.stitching import (
    STITCHING_RESOLUTION,
    StitchingSettings,
)
from openflexure_microscope_server.things.autofocus import (
    MAX_TEST_IMAGE_COUNT,
    MIN_TEST_IMAGE_COUNT,
    AutofocusParams,
    AutofocusThing,
    SmartStackParams,
)
from openflexure_microscope_server.things.background_detect import (
    ChannelDeviationLUV,
)
from openflexure_microscope_server.things.camera import BaseCamera, CaptureParams
from openflexure_microscope_server.things.camera_stage_mapping import CameraStageMapper
from openflexure_microscope_server.things.stage import BaseStage
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

    # CSM may not be set, and isn't required for a workflow. Allow for it to exist or be None
    _csm: Optional[CameraStageMapper] = lt.thing_slot()
    # Camera, stage and autofocus are all required by any scan workflow
    _cam: BaseCamera = lt.thing_slot()
    _stage: BaseStage = lt.thing_slot()
    _autofocus: AutofocusThing = lt.thing_slot()

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
            "Each specific ScanWorkflow must implement a `all_settings` method."
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
        """Overload to set the acquisition routine that happens at each scan site.

        :param settings: The settings for this scan, which should be a SettingModelType
        :param xyz_pos: The current position as a tuple or 3 ints.
        :return: A tuple of whether an image was taken, and the z-position for focus.
            If failed to find focus, returns for the focus z-position.
        """
        raise NotImplementedError(
            "Each specific ScanWorkflow must implement an acquisition routine"
        )

    def _autofocus_and_capture(
        self,
        xyz_pos: tuple[int, int, int],
        dz: int,
        images_dir: str,
        save_resolution: tuple[int, int],
    ) -> tuple[bool, Optional[int]]:
        """Autofocus and then capture, this can be used as an acquisition routine.

        :param dz: The dz for autofocus.
        :param images_dir: The path to the directory for saving images..
        :param save_resolution: The resolution to save images at.

        :return: A tuple ready to pass out of acquisition routine. In this method,
            image is always taken, so first return is True.

        """
        self._autofocus.fast_autofocus(dz=dz)
        focus_height = self._stage.get_xyz_position()[2]
        filename = f"img_{xyz_pos[0]}_{xyz_pos[1]}_{focus_height}.jpeg"
        self._cam.capture_and_save(
            jpeg_path=os.path.join(images_dir, filename),
            save_resolution=save_resolution,
        )

        return True, focus_height

    @lt.property
    def settings_ui(self) -> list[PropertyControl]:
        """A list of PropertyControl objects to create the settings in the scan tab."""
        raise NotImplementedError(
            "Each scan workflow must implement a settings_ui method."
        )


class RectGridWorkflow(ScanWorkflow[SettingModelType], Generic[SettingModelType]):
    """A generic workflow for any scan that captures images on a rectilinear grid."""

    # Redefine _csm Thing Slot, as CSM is required for any RectGridWorkflow
    _csm: CameraStageMapper = lt.thing_slot()

    overlap: float = lt.setting(default=0.45, ge=0.1, le=0.7)
    """The fraction that adjacent images should overlap in x and y.

    This must be between 0.1 and 0.7.
    """

    autofocus_dz: int = lt.setting(default=1000, ge=400, le=3000)
    """The z distance to perform an autofocus in steps.

    Must be greater than or equal to 400, and less than or equal to 3000.

    Note that 200 steps is the backlash correction size, so the value
    must be above this. 3000 is a sensible limit for 20x objectives.
    """

    # The noqa statement is because scan_name is unused but is needed for equivalence
    # with other workflows that may want to validate the scan name.
    def check_before_start(self, scan_name: str) -> None:  # noqa: ARG002
        """Before starting a scan, check that camera-stage-mapping is set.

        Raise error if:
          - camera stage mapping is not set
        """
        if self._csm.calibration_required:
            raise RuntimeError("Camera Stage Mapping is not calibrated.")

    def _calc_displacement_from_overlap(self, overlap: float) -> tuple[int, int]:
        """Use camera stage mapping to calculate x and y displacement from given overlap.

        :param overlap: The desired overlap as a fraction of the image. i.e. 0.5 means
            that each image should overlap its nearest neighbour by 50%.

        :returns: (dx, dy) - the x and y displacements in steps

        :raises RuntimeError: If there is no camera stage mapper Thing available or if CMS isn't calibrated.
        """
        csm_image_res = self._csm.image_resolution
        if csm_image_res is None:
            raise RuntimeError("CSM not set. Scan shouldn't have progressed this far.")

        # Calculate displacements in image coordinates
        dx_img = csm_image_res[1] * (1 - overlap)
        dy_img = csm_image_res[0] * (1 - overlap)

        x_move_stage = self._csm.convert_image_to_stage_coordinates(x=dx_img, y=0)
        y_move_stage = self._csm.convert_image_to_stage_coordinates(x=0, y=dy_img)

        # Assume no rotation or skew and take only the aligned axis of vector.
        # Coerce to positive integer, but correct if x and y are flipped
        if abs(x_move_stage["x"]) > abs(x_move_stage["y"]):
            return x_move_stage["x"], y_move_stage["y"]
        # If not use the other stage axes. Note "dx" will be the movement in camera y.

        self.logger.info(
            f"Based on an overlap of {self.overlap}, the stage will make steps of "
            f"{y_move_stage['x']}, {x_move_stage['y']}"
        )
        return y_move_stage["x"], x_move_stage["y"]

    def _get_stitching_settings_model(self) -> StitchingSettings:
        """Return a stitching settings model based on current settings."""
        return StitchingSettings(
            overlap=self.overlap,
            correlation_resize=STITCHING_RESOLUTION[0] / self.save_resolution[0],
        )

    def all_settings(
        self, images_dir: str
    ) -> tuple[SettingModelType, Optional[StitchingSettings]]:
        """Return the scan settings and the stitching settings.

        - `images_dir` is used to create the CaptureParams stored in the settings model.
        - The returned SettingModelType now contains param objects:
            * capture_params: CaptureParams
            * autofocus_params: AutofocusParams
            * stack_params: StackParams (if relevant)
        """
        stitching_settings = self._get_stitching_settings_model()
        dx, dy = self._calc_displacement_from_overlap(self.overlap)

        capture_params = CaptureParams(
            images_dir=images_dir, save_resolution=self.save_resolution
        )

        autofocus_params = AutofocusParams(dz=self.autofocus_dz)

        scan_settings = self._settings_model(
            overlap=self.overlap,
            dx=dx,
            dy=dy,
            capture_params=capture_params,
            autofocus_params=autofocus_params,
        )

        return scan_settings, stitching_settings

    @lt.property
    def ready(self) -> bool:
        """Whether this scanworkflow is ready to start."""
        return not self._csm.calibration_required


class HistoScanSettingsModel(BaseModel):
    """The settings for a scan with the HistoScanWorkflow.

    This includes settings calculated when starting. This will be held by smart scan
    during a scan and serialised to disk.
    """

    overlap: float
    dx: int
    dy: int
    max_dist: int
    skip_background: bool
    capture_params: CaptureParams
    autofocus_params: AutofocusParams
    smart_stack_params: SmartStackParams


class HistoScanWorkflow(RectGridWorkflow[HistoScanSettingsModel]):
    """A workflow optimised for scanning Histopathology samples.

    This workflow automatically plans its own path around a sample spiralling out from
    the centre position, scanning only where it detects sample.
    """

    display_name: str = lt.property(default="Histo Scan", readonly=True)
    ui_blurb: str = lt.property(
        default=(
            "This scan workflow is optimised for scanning H&E stained biopsies. It "
            "spirals out from the starting location, scanning only where it detects "
            "sample. It also works well for many other flat, well-featured samples."
        ),
        readonly=True,
    )

    _settings_model = HistoScanSettingsModel
    _planner_cls = SmartSpiral
    # Thing Slots
    _background_detector: ChannelDeviationLUV = lt.thing_slot()

    # Scan settings

    skip_background: bool = lt.setting(default=True)
    """Whether to detect and skip empty fields of view.

    This uses the settings from the ``BackgroundDetectThing``.
    """

    max_range: int = lt.setting(default=45000, ge=0)
    """The maximum distance in steps from the centre of the scan."""

    # Stacking settings

    stack_images_to_save: int = lt.setting(default=1, ge=1, le=9)
    """The number of images to save in a stack.

    Defaults to 1 unless you need to see either side of focus
    """

    stack_min_images_to_test: int = lt.setting(default=9, ge=5, le=13)
    """The minimum number of images to capture in a stack.

    This many images are captures and tested for focus, if the focus is not central
    enough more images may be captured. After new images are captured, this value sets
    the number of images used for checking if focus is achieved.

    Defaults to 9 which balances reliability and speed.
    """

    stack_dz: int = lt.setting(default=50, ge=10, le=400)
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
        """Return the workflow settings and stitching settings.

        :param images_dir: The directory that images are to be written to.
        :return: A tuple containing the settings model for this workflow and the
            settings model for stitching.
        """
        stitching_settings = self._get_stitching_settings_model()
        dx, dy = self._calc_displacement_from_overlap(self.overlap)

        capture_params = CaptureParams(
            images_dir=images_dir,
            save_resolution=self.save_resolution,
        )
        autofocus_params = AutofocusParams(dz=self.autofocus_dz)
        smart_stack_params = self.create_smart_stack_params()

        scan_settings = HistoScanSettingsModel(
            overlap=self.overlap,
            max_dist=self.max_range,
            dx=dx,
            dy=dy,
            skip_background=self.skip_background,
            capture_params=capture_params,
            autofocus_params=autofocus_params,
            smart_stack_params=smart_stack_params,
        )

        return scan_settings, stitching_settings

    def create_smart_stack_params(
        self,
    ) -> SmartStackParams:
        """Set up the parameters used for all smart stacks in a scan.

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
            save_on_failure=not self.skip_background,
        )

    def pre_scan_routine(self, settings: HistoScanSettingsModel) -> None:
        """Autofocus before starting the scan.

        :param settings: The settings for this scan as a HistoScanSettingsModel
        """
        self._autofocus.looping_autofocus(
            dz=settings.autofocus_params.dz, start="centre"
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
        if settings.skip_background:
            # If skipping background, take an image to check if current field of view
            # is background
            image_array = self._cam.grab_as_array(stream_name="lores")
            capture_image, bg_message = self._background_detector.image_is_sample(
                image_array
            )
            del image_array

            if not capture_image:
                # Return early if the image is background.
                msg = f"Skipping {xyz_pos} as it is {bg_message}."
                self.logger.info(msg)
                return False, None

        focus_height: Optional[int]
        focused, focus_height = self._autofocus.run_smart_stack(
            stack_parameters=settings.smart_stack_params,
            capture_parameters=settings.capture_params,
            autofocus_parameters=settings.autofocus_params,
        )
        # An image was captured if we are focussed or we are not skipping background.
        imaged = focused or settings.smart_stack_params.save_on_failure

        if not imaged:
            msg = f"Stack failed at {xyz_pos}. Treating as background."
            self.logger.info(msg)

        # run_smart_stage always returns a focus height for the sharpest image even
        # if it failed to find a good focus. Set to None if not focussed.
        if not focused:
            focus_height = None

        return imaged, focus_height

    @lt.property
    def settings_ui(self) -> list[PropertyControl]:
        """A list of PropertyControl objects to create the settings in the scan tab."""
        return [
            property_control_for(
                self, "overlap", label="Image Overlap (0.1-0.7)", step=0.05
            ),
            property_control_for(
                self, "stack_images_to_save", label="Images in Stack to Save"
            ),
            property_control_for(
                self,
                "stack_min_images_to_test",
                label="Minimum number of images to test for focus",
            ),
            property_control_for(self, "stack_dz", label="Stack dz (steps)", step=5),
            property_control_for(
                self, "autofocus_dz", label="Autofocus Range (steps)", step=200
            ),
            property_control_for(
                self, "max_range", label="Maximum Distance (steps)", step=1000
            ),
            property_control_for(
                self, "skip_background", label="Detect and Skip Empty Fields "
            ),
        ]


class RegularGridSettingsModel(BaseModel):
    """The settings for a scan with a regular grid of dx and dy for x_count, y_count steps.

    This includes settings calculated when starting. This will be held by smart scan
    during a scan and serialised to disk.
    """

    overlap: float
    dx: int
    dy: int
    x_count: int
    y_count: int
    style: Literal["snake", "raster"]
    capture_params: CaptureParams
    autofocus_params: AutofocusParams


class RegularGridWorkflow(RectGridWorkflow[RegularGridSettingsModel]):
    """A base workflow for any workflow that uses a regular rectangular grid."""

    x_count: int = lt.setting(default=3, ge=1)
    """The number of columns in the scan."""
    y_count: int = lt.setting(default=2, ge=1)
    """The number of rows in the scan."""

    _settings_model = RegularGridSettingsModel
    _planner_cls = RegularGridPlanner
    _grid_style: Literal["snake", "raster"]

    def all_settings(
        self, images_dir: str
    ) -> tuple[RegularGridSettingsModel, Optional[StitchingSettings]]:
        """Return the workflow and stitching settings.

        :param images_dir: The directory that images are to be written to.
        :return: A tuple containing the settings model for this workflow and the
            settings model for stitching.
        """
        stitching_settings = self._get_stitching_settings_model()
        dx, dy = self._calc_displacement_from_overlap(self.overlap)

        capture_params = CaptureParams(
            images_dir=images_dir,
            save_resolution=self.save_resolution,
        )

        autofocus_params = AutofocusParams(dz=self.autofocus_dz)

        scan_settings = self._settings_model(
            overlap=self.overlap,
            dx=dx,
            dy=dy,
            x_count=self.x_count,
            y_count=self.y_count,
            style=self._grid_style,
            capture_params=capture_params,
            autofocus_params=autofocus_params,
        )

        return scan_settings, stitching_settings

    def pre_scan_routine(self, settings: RegularGridSettingsModel) -> None:
        """Perform these steps before starting the scan.

        In this case, only autofocus.

        :param settings: The settings for this scan as as the relevant SettingsModel type.
        """
        self._autofocus.looping_autofocus(
            dz=settings.autofocus_params.dz, start="centre"
        )

    def new_scan_planner(
        self, settings: RegularGridSettingsModel, position: Mapping[str, int]
    ) -> ScanPlanner:
        """Return a new scan planner object.

        :param settings: The settings for this scan as a SnakeSettingsModel
        :param position: The starting position as a mapping of axes names to int.
        """
        planner_settings = {
            "dx": settings.dx,
            "dy": settings.dy,
            "x_count": settings.x_count,
            "y_count": settings.y_count,
            "style": settings.style,
        }
        return self._planner_cls(
            initial_position=(position["x"], position["y"]),
            planner_settings=planner_settings,
        )

    def acquisition_routine(
        self, settings: RegularGridSettingsModel, xyz_pos: tuple[int, int, int]
    ) -> tuple[bool, Optional[int]]:
        """Autofocus and capture.

        :param settings: The settings for this scan as a RegularGridSettingsModel
        :param xyz_pos: The current position as a tuple or 3 ints.
        :return: A tuple of whether an image was taken, and the z-position for focus.
            If failed to find focus, returns for the focus z-position.
        """
        return self._autofocus_and_capture(
            xyz_pos=xyz_pos,
            dz=settings.autofocus_params.dz,
            images_dir=settings.capture_params.images_dir,
            save_resolution=settings.capture_params.save_resolution,
        )

    @lt.property
    def settings_ui(self) -> list[PropertyControl]:
        """A list of PropertyControl objects to create the settings in the scan tab."""
        return [
            property_control_for(
                self, "overlap", label="Image Overlap (0.1-0.7)", step=0.05
            ),
            property_control_for(self, "x_count", label="Number of columns"),
            property_control_for(self, "y_count", label="Number of rows"),
            property_control_for(self, "autofocus_dz", label="Autofocus Range (steps)"),
        ]


class SnakeWorkflow(RegularGridWorkflow):
    """A workflow optimised for snaking around samples.

    This workflow generates a list of coordinates in a rectangle, and snakes
    around them from the top left (assuming positive dx and dy).
    """

    display_name: str = lt.property(default="Snake Scan", readonly=True)
    ui_blurb: str = lt.property(
        default=(
            "This scan workflow is optimised for scanning over a rectangle. It "
            "snakes down and right from the starting point, over a defined grid."
        ),
        readonly=True,
    )
    _grid_style = "snake"


class RasterWorkflow(RegularGridWorkflow):
    """A workflow optimised for snaking around samples.

    This workflow generates a list of coordinates in a rectangle, and always
    moves right across a row, then moves down a row while moving to the starting
    column (assuming positive dx and dy).
    """

    display_name: str = lt.property(default="Raster Scan", readonly=True)
    ui_blurb: str = lt.property(
        default=(
            "This scan workflow is optimised for performing a raster scan over a rectangle. It "
            "always moves down and right from the starting point, over a defined grid."
        ),
        readonly=True,
    )

    _grid_style = "raster"
