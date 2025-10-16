"""File contains all the functions used to measure the range of motion.

The range of motion is measured by first taking 5 'medium' sized steps which gives enough positions
to predict future z positions. Next, one 'big' step is taken followed by 3
'small' steps to test that the stage is still moving as expected and has not reached the edge.
Once the edge has been found and to account for the possibility that a 'big'
step was taken just before the edge was reached, the stage is moved in a sequence
of increasing pixel sizes in the opposite direction until motion is detected. This is
position is taken as the true final position.

Throughout the test, parasitic motion(motion in the axis not being measured)
is tracked and an error is raised if it exceeds a minimum amount. Currently
this is 10% of the expected motion is the measured axis.
"""

from typing import Literal, Any, Optional, overload
import time
from dataclasses import dataclass
from threading import Lock

from scipy.optimize import curve_fit
import numpy as np

from camera_stage_mapping import fft_image_tracking
import labthings_fastapi as lt

from openflexure_microscope_server.utilities import quadratic

# Things
from .autofocus import AutofocusThing
from .camera_stage_mapping import CameraStageMapper
from .camera import CameraDependency as CamDep
from .stage import StageDependency as StageDep

CSMDep = lt.deps.direct_thing_client_dependency(
    CameraStageMapper, "/camera_stage_mapping/"
)
AutofocusDep = lt.deps.direct_thing_client_dependency(AutofocusThing, "/autofocus/")

## Size of movement in percentage of field of view
SMALL_STEP = 20
MEDIUM_STEP = 50
BIG_STEP = 200

PARASITIC_MOTION_TOL = 0.1


class RomDataTracker:
    """Class for tracking range of motion data.

    The attributes storing data are:

    * ``stage_coords`` A list of the the stage coordinates at each measurement location
    * ``displacements`` A list of the displacement calculated after each movement
    """

    def __init__(self) -> None:
        """Define useful data tracked throughout test."""
        self.stage_coords: list[dict[str, int]] = []
        self.offsets: list[dict[str, float]] = []

    def record_movement(
        self, current_pos: dict[str, int], offset: dict[str, int]
    ) -> None:
        """Record the current position and the measured offset of the last move."""
        self.stage_coords.append(current_pos)
        self.offsets.append(offset)

    @property
    def final_position(self) -> dict[str, int]:
        """The last stage coordinate recorded."""
        return self.stage_coords[-1].copy()

    def predict_z_displacament(
        self,
        movement: dict[str, int],
        stage_position: dict[str, int],
        csm_matrix: np.ndarray,
    ) -> float:
        """Predict the z-displacement needed for a given movement.

        :param movement: The movement to be performed in image coordinates.
        :param stage_position: The current stage position in stage coordinates.
        :param csm_matrix: The camera stage mapping matrix.
        :returns: The predicted relative z displacement needed to stay in focus.
        """
        pixel_step = {
            "x": 1 / csm_matrix[0][1],
            "y": 1 / csm_matrix[1][0],
        }

        axis = _axis_from_movement_dict(movement)

        lateral_positions = [i[axis] for i in self.stage_coords]  # x or y positions
        z_positions = [i["z"] for i in self.stage_coords]
        fit_params, *_others = curve_fit(quadratic, lateral_positions, z_positions)
        z_dest = quadratic(
            stage_position[axis] + (movement[axis] / pixel_step[axis]), *fit_params
        )

        return z_dest - stage_position["z"]


@dataclass
class RomDeps:
    """Grouped dependencies for the Range of motion Thing.

    These are used to pass the dependencies from actions to other sub-functions.
    """

    autofocus: AutofocusDep
    stage: StageDep
    cam: CamDep
    csm: CSMDep
    logger: lt.deps.InvocationLogger


class ParasiticMotionError(Exception):
    """Custom exception raised when parasitic motion is detected.

    Parasitic motion is when motion in the direction not being measured
    is too high.
    """


class RangeofMotionThing(lt.Thing):
    """A class used to measure the range of motion of the stage in X and Y."""

    calibrated_range = lt.ThingSetting(
        initial_value=None, model=Optional[list[int, int]], readonly=True
    )

    def __init__(self) -> None:
        """Initialise and create the lock."""
        super().__init__()
        self._lock = Lock()
        self._stream_resolution: Optional[tuple[int, int]] = None
        self._rom_data = RomDataTracker()

    @lt.thing_action
    def perform_rom_test(
        self,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CamDep,
        csm: CSMDep,
        logger: lt.deps.InvocationLogger,
    ) -> dict[str, Any]:
        """Measures the range of motion of the stage across the x and y axes.

        :param autofocus: A raw_thing_client dependency for autofocus.
        :param stage: A raw_thing_client depeendency for the microscope stage.
        :param cam: A raw_thing_client depeendency for the camera.
        :param csm: A raw_thing_client depeendency for camera stage mapping.
        :param logger: A raw_thing_client depeendency for the logger.
        :return: Results dictionary separated into keys of each axis and direction.
        """
        got_lock = self._lock.acquire(blocking=False)
        if not got_lock:
            raise RuntimeError("Trying to run ROM test when a test is already running.")

        rom_deps = RomDeps(
            autofocus=autofocus, stage=stage, csm=csm, cam=cam, logger=logger
        )
        logger.info(
            "Using the stage to measure the Range of Motion. "
            "Please ensure you are using a big enough sample."
        )
        start_time = time.time()

        self._set_stream_resolution(cam)

        # The total range for the two axes under test
        step_range = []

        for axis in ["x", "y"]:
            # The final position of the axis under test in the given direction
            axis_limits = []
            for axis_dir in [1, -1]:
                # Create a new tracker at start of measurement.
                self._rom_data = RomDataTracker()
                self._move_until_edge(axis=axis, direction=axis_dir, rom_deps=rom_deps)
                # Append final position from tracker
                axis_limits.append(self._rom_data.final_position[axis])
            # Calculate step range.
            step_range.append(abs(axis_limits[0] - axis_limits[1]))

        total_time = time.time() - start_time
        logger.info(f"Range of motion is {step_range[0]} x {step_range[1]} steps")
        self.calibrated_range = step_range

        return {
            "Time": total_time,
            "CSM Matrix": csm.image_to_stage_displacement_matrix.tolist(),
            "Step Range": step_range,
        }

    def _set_stream_resolution(self, cam: CamDep) -> None:
        """Set the self._stream_reolution attribute by reading camera.

        :param cam: The camera dependency.
        """
        stream_shape = cam.grab_as_array().shape
        # Swap axes as numpy is [y, x]
        self._stream_resolution = [stream_shape[1], stream_shape[0]]

    def _move_until_edge(
        self,
        axis: Literal["x", "y"],
        direction: Literal[1, -1],
        rom_deps: RomDeps,
    ) -> dict:
        """Move in one direction until no movement is detected.

        :param rom_deps: All dependencies that were passed to the calling Action
        :param axis: The axis which is being measured. This must be 'x' or 'y'.
        :param direction: The direction which is being measured. This must be 1 or -1.
        :return: Results dictionary containing stage positions,
           correlations and the final position.
        """
        # Start by performing an autofocus and recording starting position
        rom_deps.autofocus.looping_autofocus(dz=1000)
        starting_position = list(rom_deps.stage.position.values())

        try:
            dir_str = "positive" if direction == 1 else "negative"
            rom_deps.logger.info(
                f"Beginning the {axis}-axis in the {dir_str} direction"
            )

            self._rom_data.stage_coords.append(rom_deps.stage.position)

            rom_deps.logger.info("Moving the stage in 5 medium sized steps.")
            self._initial_moves_for_z_prediction(
                direction=direction,
                axis=axis,
                rom_deps=rom_deps,
            )

            still_moving = True
            # Loop taking 1 big step followed by 3 small steps to check if the
            # stage is moving as expected or has reached end of range of motion.
            # Stop once end of range of motion is detected.
            while still_moving:
                self._big_z_corrected_movement(
                    axis=axis, direction=direction, rom_deps=rom_deps
                )

                # Autofocus and record position
                rom_deps.autofocus.looping_autofocus(dz=800)
                self._rom_data.stage_coords.append(rom_deps.stage.position)

                # Perform small moves to check stage is still moving.
                still_moving = self._stage_still_moves(
                    axis=axis,
                    direction=direction,
                    rom_deps=rom_deps,
                )

            # Stage may have crashed during a large move. Move stage back until motion
            # is detected
            rom_deps.logger.info("Moving stage back until motion is detect")
            self._move_back_until_motion_detected(
                axis=axis,
                direction=direction,
                rom_deps=rom_deps,
            )

            # Replace final position.
            self._rom_data.stage_coords[-1] = rom_deps.stage.position

        finally:
            rom_deps.stage.move_absolute(
                x=starting_position[0],
                y=starting_position[1],
                z=starting_position[2],
                block_cancellation=True,
            )

    def _img_percentate_to_img_coords(
        self, fov_perc: int, axis: Literal["x", "y"]
    ) -> float:
        """For a given image percentage and axis return the distance in img coords.

        :param fov_perc: The percentage of field of view the stage should move by.
        :param axis: The resolution of the stream from the camera.
        :return: Distance in image coordinates (pixels)
        """
        if self._stream_resolution is None:
            raise RuntimeError(
                "Stream resolution mut be set before generating movement in coords"
            )

        img_index = 0 if axis == "x" else 1
        return (fov_perc / 100) * self._stream_resolution[img_index]

    def _movement_in_img_coords(
        self,
        fov_perc: int,
        axis: Literal["x", "y"],
        direction: Literal[1, -1],
    ) -> dict[str, float]:
        """Return the dictionary for a move in image coordinates.

        This dictionary can be passed directly to csm.move_in_image_coordinates

        :param fov_perc: The percentage of field of view the stage should move by.
        :param axis: The resolution of the stream from the camera.
        :param direction: The direction the stage moves.

        :return: The movement size in image coordinates
        """
        distance = self._img_percentate_to_img_coords(fov_perc=fov_perc, axis=axis)
        if axis == "x":
            return {"x": distance * direction, "y": 0}
        return {"x": 0, "y": distance * direction}

    def _initial_moves_for_z_prediction(
        self,
        direction: Literal[1, -1],
        axis: Literal["x", "y"],
        rom_deps: RomDeps,
    ) -> None:
        """Perform 5 medium sized moves with autofocus for z feed-forward.

        z-feed forward allows prediction of the z-position as the stage moves. For the
        feed forward calculation to work an initial number of measurements must be
        taken. This method performs these initial measurements.

        :param direction: The direction the stage moves.
        :param axis: The axis which is being measured. This must be 'x' or 'y'.
        :param rom_deps: All dependencies that were passed to the calling Action
        """
        movement = self._movement_in_img_coords(
            fov_perc=MEDIUM_STEP, axis=axis, direction=direction
        )
        for _loop in range(5):
            offset = self._move_and_measure(movement=movement, rom_deps=rom_deps)

            rom_deps.logger.info(f"Offset measured as {offset[axis]}")

            self._rom_data.record_movement(rom_deps.stage.position, offset)
            _detect_parasitic_motion(movement, offset)

    def _big_z_corrected_movement(
        self, axis: Literal["x", "y"], direction: Literal[1, -1], rom_deps: RomDeps
    ) -> None:
        """Take one big move with feed-forward z-correction.

        The size is defined by the BIG_STEP constant.

        :param axis: The axis to move in.
        :param direction: The direction to move in.
        :param rom_deps: All dependencies that were passed to the calling Action
        """
        big_movement = self._movement_in_img_coords(
            fov_perc=BIG_STEP, axis=axis, direction=direction
        )
        z_disp = self._rom_data.predict_z_displacament(
            movement=big_movement[axis],
            stage_position=rom_deps.stage.position,
            csm_matrix=rom_deps.csm.image_to_stage_displacement_matrix,
        )
        rom_deps.stage.move_relative(z=z_disp)
        rom_deps.csm.move_in_image_coordinates(**big_movement)

    def _stage_still_moves(
        self,
        axis: Literal["x", "y"],
        direction: Literal[1, -1],
        rom_deps: RomDeps,
    ) -> bool:
        """Carry out 3 small moves in a given direction and axis.

        Each position after the first is correlated with the previous position
        to check the stage has moved as far as it should. If the correlation is
        less than expected, 3 attempts are made to refocus the image to ensure that
        image quality is not causing the correlation to be unsuccessful. If the correlation
        is still too low then the edge is found.

        Delta is updated and tracked after each move.

        :param stream_resolution: The resolution of the stream from the camera.
        :param direction: The direction the stage moves.
        :param axis: The axis which is being measured. This must be 'x' or 'y'.
        :param rom_deps: All dependencies that were passed to the calling Action
        """
        movement = self._movement_in_img_coords(
            fov_perc=SMALL_STEP, axis=axis, direction=direction
        )
        abs_min_offset = abs(movement[axis] * 0.65)

        for _loop in range(3):
            offset = self._move_and_measure(
                movement=movement,
                rom_deps=rom_deps,
                # Don't autofocus initially
                perform_autofocus=False,
                # But retry focus 3 times if detected motion is too small
                max_autofocus_repeats=3,
                abs_min_offset=abs_min_offset,
            )
            rom_deps.logger.info(f"Offset measured as {offset[axis]}")

            self._rom_data.record_movement(rom_deps.stage.position, offset)
            _detect_parasitic_motion(movement, offset)

            if abs(offset[axis]) < abs_min_offset:
                # If the offset is below the abs min offset, the edge has been found.
                rom_deps.logger.info("Edge has been found.")
                return False
        # If we reached here the stage is still moving fine
        return True

    def _move_back_until_motion_detected(
        self,
        axis: Literal["x", "y"],
        direction: Literal[1, -1],
        rom_deps: RomDeps,
    ) -> None:
        """Move the stage against the direction of test unil motion is detected.

        In the case that the stage has reached the end of the motion, this method moves
        the motor in the opposite direction until motion is detected.

        :param axis: The axis in which the stage is moving. This must be 'x' or 'y'.
        :param direction: The direction in which the stage was moving during the test,
            this method will move in the opposite direction.
        :param rom_deps: All dependencies that were passed to the calling Action
        """
        # Array of increasing pixel sizes (powers of 2 from 1 to 512)
        displacements = [2**i for i in range(10)]

        motion_minimum = 20  # minimum number of pixels for motion to be detected

        movement = {"x": 0, "y": 0}

        for displacement in displacements:
            # Increment movement
            movement[axis] = displacement * direction * -1
            rom_deps.logger.info(f"Testing with step size {movement[axis]}")

            offset = self._move_and_measure(
                movement=movement, rom_deps=rom_deps, perform_autofocus=False
            )

            rom_deps.logger.info(f"Offset measured as {abs(offset[axis])}")
            if abs(offset[axis]) > motion_minimum:
                rom_deps.logger.info("Motion detected.")
                return
        # If this point is reached then motion is never detected
        raise RuntimeError("Cannot detect motion again after reaching end of range.")

    def _move_and_measure(
        self,
        movement: dict[str, float],
        rom_deps: RomDeps,
        perform_autofocus: bool = True,
        max_autofocus_repeats: int = 0,
        abs_min_offset: float = 0.0,
    ) -> dict[str, float]:
        """Move the stage and measure the offset between the two positions.

        :param movement: A dictionary containing the distance to move in image coords.
        :param rom_deps: All dependencies that were passed to the calling Action
        :param perform_autofocus: Set to False to disable atutofocus after move.
            Default is  True
        :param max_autofocus_repeats: The number of times to repeat the focus if the
            detected (on-axis) offset is below ``abs_min_offset``. This will only work
            if ``abs_min_offset`` is also set
        :param abs_min_offset: The absolute minimum (on-axis) offset, under which the
            autofocus is repeated.
        :return: All required data for the next move. This includes the updated delta
            value and offset.
        """
        # Take image before move
        before_img = rom_deps.cam.grab_as_array()
        # Move and autofocus if required
        rom_deps.csm.move_in_image_coordinates(**movement)
        if perform_autofocus:
            rom_deps.autofocus.looping_autofocus(dz=800)
        # Take image and calculate offset
        offset = self._offset_from(before_img, rom_deps=rom_deps)

        if max_autofocus_repeats > 0:
            axis = _axis_from_movement_dict(movement)
            af_repeats = 0
            while abs(offset[axis]) < abs_min_offset:
                af_repeats += 1
                rom_deps.logger.info(
                    f"Motion not detected. Refocusing to check. Attempt {af_repeats}/3."
                )
                rom_deps.autofocus.looping_autofocus(dz=800)
                # Re-take image and calculate offset
                offset = self._offset_from(before_img, rom_deps=rom_deps)
                if af_repeats >= max_autofocus_repeats:
                    # break if the maximum number of tries are exceeded.
                    break

        return offset

    def _offset_from(
        self, before_img: np.ndarray, rom_deps: RomDeps
    ) -> dict[str, float]:
        """Take an image and calculate the offset from an input image.

        :param before_img: The image the offset should be calculated with respect to.
        :param rom_deps: All dependencies that were passed to the calling Action
        :return: The calculated offset as a dictionary in pixels
        """
        after_img = rom_deps.cam.grab_as_array()
        offset = fft_image_tracking.displacement_between_images(
            image_0=before_img,
            image_1=after_img,
            sigma=10,
            fractional_threshold=0.1,
            pad=True,
        )
        return {"x": offset[1], "y": offset[0]}


@overload
def _axis_from_movement_dict(
    movement: dict[str, float], return_other: bool = False
) -> str: ...


@overload
def _axis_from_movement_dict(
    movement: dict[str, float], return_other: bool = True
) -> tuple[str, str]: ...


def _axis_from_movement_dict(movement: dict[str, float], return_other: bool = False):
    """Return the axis that a given movement dictionary moves in.

    For example: ``_axis_from_movement_dict({"x": 10, "y":0})`` will return ``x``.

    :param movement: The movement dictionary.
    :param return_other: If True return a tuple with the first value being the movement
        axis and the second being the other axis. Default is False
    :return: The movement axis (and optionally the other axis) as strings.
    """
    # Not exclusive or, this errors if both axes are zero or neither axes are zero.
    if not ((movement["x"] == 0) ^ (movement["y"] == 0)):
        raise ValueError("Either x or y movement should be zero, but not both.")

    if return_other:
        return ("y", "x") if movement["x"] == 0 else ("x", "y")
    return "y" if movement["x"] == 0 else "x"


def _detect_parasitic_motion(
    movement: dict[str, float], offset: dict[str, float]
) -> None:
    """Compare a desired movement to measured offset and error if parasitic motion is too high.

    :param movement: The movement dictionary in image coordinates.
    :param offset: The offset calculated from correlation.
    """
    movement_axis, other_axis = _axis_from_movement_dict(movement, return_other=True)
    parasitic_motion = abs(offset[other_axis])
    max_parasitic_motion = abs(movement[movement_axis] * PARASITIC_MOTION_TOL)
    if parasitic_motion > max_parasitic_motion:
        raise ParasiticMotionError(
            f"Parasitic motion detected. Detected motion of {parasitic_motion} pixels "
            f"this exceeds a maximum for this move of {max_parasitic_motion} pixels."
        )
