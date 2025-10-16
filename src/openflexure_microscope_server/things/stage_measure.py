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

from typing import Literal, Any, Optional
import time
from dataclasses import dataclass

from scipy.optimize import curve_fit
from PIL import Image
import numpy as np
import numpy.typing as npt

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


class RomDataTracker:
    """Class for tracking range of motion data."""

    # TODO: Find out what these variable are
    def __init__(
        self,
        stage_coords: Optional[list[dict[str, int]]] = None,
        cor_lat_steps: Optional[list[npt.ArrayLike]] = None,
        delta: Optional[dict[str, int]] = None,
    ) -> None:
        """Define useful data tracked throughout test."""
        self.stage_coords = [] if stage_coords is None else stage_coords
        self.cor_lat_steps = [] if cor_lat_steps is None else cor_lat_steps
        self.delta = {"x": 0, "y": 0} if delta is None else delta

    def measure(self, current_pos: dict[str, int], cor: npt.ArrayLike) -> None:
        """Store useful data."""
        self.stage_coords.append(current_pos)
        self.cor_lat_steps.append(cor)


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


def _parasitic_detect(delta: float, max_allowed_delta: float) -> None:
    """Compare two values and raise parasitic motion error."""
    if delta > max_allowed_delta:
        raise ParasiticMotionError(
            f"Parasitic motion detected. {delta} is greater than {max_allowed_delta}"
        )


def _generate_move_dicts(
    fov_perc: int,
    stream_resolution: list[int],
    direction: Literal[1, -1],
    factor: float = 1,
) -> dict[str, float]:
    """Create a single dictionary of x and y moves for moving in image coordinates.

    This can either be used to create move sizes or minimum move sizes. For example,
    the stage must move a minimum distance for a move to be considered successful.
    We define the minimum with this function. This is also used to define the maximally
    allowed motion in the wrong axis.

    :param fov_perc: The percentage of field of view the stage should move by.
    :param stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :param factor: Reduction factor which allows for minimum move sizes to be created.
    :return: A dictionary with keys 'x' and 'y' with a pixel distance move the stage can make.
    """
    return {
        "x": (fov_perc / 100) * stream_resolution[0] * factor * direction,
        "y": (fov_perc / 100) * stream_resolution[1] * factor * direction,
    }  # factor used for creating minimum offsets.


def _predict_z(
    positions: list,
    axis: Literal["x", "y"],
    relative_move: float,
    stage: StageDep,
    csm: CSMDep,
) -> float:
    """Predict the next z position for a move using previous positions.

    :param positions: The list of positions used for predicting z.
        This will be a list of all previous positions.
    :param axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :param relative_move: The move which the function is trying to predict z for.
        Here, this is inputted with units of pixels.
    :param stage: A direct_thing_client dependency for the the microscope stage.
    :param csm: A direct_thing_client dependency for camera stage mapping.
    :return: A number of pixels the stage needs to move in z.
    """
    pixel_step = {
        "x": 1 / csm.image_to_stage_displacement_matrix[0][1],
        "y": 1 / csm.image_to_stage_displacement_matrix[1][0],
    }

    lateral_positions = [i[axis] for i in positions]  # x or y positions
    z_positions = [i["z"] for i in positions]
    fit_params, *_others = curve_fit(quadratic, lateral_positions, z_positions)
    z_dest = quadratic(
        stage.position[axis] + (relative_move / pixel_step[axis]), *fit_params
    )

    return z_dest - stage.position["z"]


def _move_and_measure(
    step_size: dict[str, float],
    axis: Literal["x", "y"],
    data: RomDataTracker,
    image1: npt.ArrayLike,
    autofocus_proc: bool,
    rom_deps: RomDeps,
) -> tuple[npt.ArrayLike, str]:
    """Move the stage and measure the offset between the two positions.

    :param step_size: A dictionary with keys 'x' and 'y' with pixel distances.
    :param axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :param data: The object used to track stage coordinates, correlation and delta.
    :param image1: An image taken before moving to be correlated with image2.
    :param rom_deps: All dependencies that were passed to the calling Action
    :return: All required data for the next move. This includes the updated delta value and offset.
        Also returns what wrong_axis is i.e. if the direction is 'x', wrong_axis = 'y'.
    """
    if axis == "x":
        rom_deps.csm.move_in_image_coordinates(x=step_size["x"], y=0)
        wrong_axis = "y"
    else:
        rom_deps.csm.move_in_image_coordinates(x=0, y=step_size["y"])
        wrong_axis = "x"
    if autofocus_proc:
        rom_deps.autofocus.looping_autofocus(dz=800)
    image2 = np.array(Image.open(rom_deps.cam.grab_jpeg().open()))
    offset = fft_image_tracking.displacement_between_images(
        image_0=image1, image_1=image2, sigma=10, fractional_threshold=0.1, pad=True
    )  # Units is pixels
    data.delta["x"] = int(offset[1])
    data.delta["y"] = int(offset[0])

    return offset, wrong_axis


def _acquire_z_predict_points(
    stream_resolution: list[int],
    direction: Literal[1, -1],
    axis: Literal["x", "y"],
    data: RomDataTracker,
    rom_deps: RomDeps,
) -> None:
    """Complete 5 medium sized steps to collect stage coordinates for prediction.

    Delta is updated and tracked after each move.

    :params stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :params axis: The axis which is being measured. This must be 'x' or 'y'.
    :params data: The object used to track stage coordinates, correlation and delta.
    :param rom_deps: All dependencies that were passed to the calling Action
    :return: Stage_coords and cor_lat_steps are lists of data tracked throughout the test.
    """
    wrong_axis_max_medium = _generate_move_dicts(
        MEDIUM_STEP, stream_resolution, direction, factor=0.1
    )
    for _loop in range(5):
        image1 = rom_deps.cam.grab_as_array()
        offset, wrong_axis = _move_and_measure(
            step_size=_generate_move_dicts(MEDIUM_STEP, stream_resolution, direction),
            axis=axis,
            data=data,
            image1=image1,
            autofocus_proc=True,
            rom_deps=rom_deps,
        )

        rom_deps.logger.info(f"Offset measured as {data.delta[axis]}")

        data.measure(rom_deps.stage.position, offset)

        _parasitic_detect(
            delta=abs(data.delta[wrong_axis]),
            max_allowed_delta=abs(wrong_axis_max_medium[wrong_axis]),
        )


def _check_stage_operation(
    stream_resolution: list[int],
    direction: Literal[1, -1],
    axis: Literal["x", "y"],
    data: RomDataTracker,
    minimum_offset_small: dict[str, float],
    rom_deps: RomDeps,
) -> None:
    """Carries out 3 small moves in a given direction and axis.

    Each position after the first is correlated with the previous position
    to check the stage has moved as far as it should. If the correlation is
    less than expected, 3 attempts are made to refocus the image to ensure that
    image quality is not causing the correlation to be unsuccessful. If the correlation
    is still too low then the edge is found.

    Delta is updated and tracked after each move.

    :params stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :params axis: The axis which is being measured. This must be 'x' or 'y'.
    :params data: The object used to track stage coordinates, correlation and delta.
    :params minimum_offset_small: A dictionary containing the minimum values for
        a successful correlation.
    :param rom_deps: All dependencies that were passed to the calling Action
    :return: Stage_coords and cor_lat_steps are lists of data tracked throughout the test.
    """
    failure_count = 0

    for _loop in range(3):
        image1 = rom_deps.cam.grab_as_array()
        offset, wrong_axis = _move_and_measure(
            step_size=_generate_move_dicts(SMALL_STEP, stream_resolution, direction),
            axis=axis,
            data=data,
            image1=image1,
            autofocus_proc=False,
            rom_deps=rom_deps,
        )
        rom_deps.logger.info(f"Offset measured as {data.delta[axis]}")

        # If correlation is too small, refocuses and capture new image 3 times.
        while (
            np.abs(data.delta[axis]) < np.abs(minimum_offset_small[axis])
            and failure_count < 3
        ):
            rom_deps.logger.info(
                f"Correlation failed. Refocusing to check. Attempt {failure_count + 1}/3"
            )
            rom_deps.autofocus.looping_autofocus(dz=1000)
            image2 = rom_deps.cam.grab_as_array()
            failure_count += 1
            offset = fft_image_tracking.displacement_between_images(
                image_0=image1,
                image_1=image2,
                sigma=10,
                fractional_threshold=0.1,
                pad=True,
            )
            # Units is pixels
            data.delta["x"] = int(offset[1])
            data.delta["y"] = int(offset[0])
            rom_deps.logger.info(
                f"Displacement found was {data.delta[axis]}.\
                Minimum offset is {minimum_offset_small[axis]}"
            )

        data.measure(rom_deps.stage.position, offset)

        _parasitic_detect(
            abs(data.delta[wrong_axis]),
            abs(
                _generate_move_dicts(
                    SMALL_STEP, stream_resolution, direction, factor=0.1
                )[wrong_axis]
            ),
        )

        # this means the edge has been found
        if np.abs(data.delta[axis]) < np.abs(minimum_offset_small[axis]):
            rom_deps.logger.info("Edge has been found.")
            break


def _motion_detection(
    axis: Literal["x", "y"],
    direction: Literal[1, -1],
    rom_deps: RomDeps,
) -> dict[str, int]:
    """Move the stage until motion is detected along a specified axis and direction.

    :params axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :params direction: The direction in which the stage was moving
        previous to motion detection being used.
    :param rom_deps: All dependencies that were passed to the calling Action
    """
    # Array of increasing pixel sizes (powers of 2 from 1 to 512)
    displacements = [2**i for i in range(10)]

    motion_minimum = 20  # minimum number of pixels for motion to be detected

    this_motion_step = {"x": 0, "y": 0}

    delta = {"x": 0, "y": 0}

    for loop in range(np.shape(displacements)[0]):
        this_motion_step[axis] = displacements[loop] * direction * -1
        rom_deps.logger.info(f"Testing with step size {this_motion_step[axis]}")
        image1 = rom_deps.cam.grab_as_array()
        rom_deps.csm.move_in_image_coordinates(
            x=this_motion_step["x"], y=this_motion_step["y"]
        )
        image2 = rom_deps.cam.grab_as_array()
        offset = fft_image_tracking.displacement_between_images(
            image_0=image1,
            image_1=image2,
            sigma=10,
            fractional_threshold=0.1,
            pad=True,
        )
        delta["x"] = int(offset[1])
        delta["y"] = int(offset[0])
        rom_deps.logger.info(f"Offset measured as {np.abs(delta[axis])}")
        if np.abs(delta[axis]) > motion_minimum:
            rom_deps.logger.info("Motion detected.")
            break

    return rom_deps.stage.position


class RangeofMotionThing(lt.Thing):
    """A class used to measure the range of motion of the stage in X and Y."""

    calibrated_range = lt.ThingSetting(
        initial_value=None, model=Optional[list[int, int]], readonly=True
    )

    @lt.thing_action
    def rom_main(
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
        rom_deps = RomDeps(
            autofocus=autofocus, stage=stage, csm=csm, cam=cam, logger=logger
        )
        logger.info(
            "Using the stage to measure the Range of Motion. "
            "Please ensure you are using a big enough sample."
        )
        start_time = time.time()
        rom_json = {}

        # Loop through all axes and directions.
        for axis_dir in [["x", 1], ["x", -1], ["y", 1], ["y", -1]]:
            axis_dir_results = self._rom_axis(
                axis=axis_dir[0],
                direction=axis_dir[1],
                rom_deps=rom_deps,
            )
            # Save results from single axis and direction
            rom_json[
                f"{'positive' if axis_dir[1] == 1 else 'negative'} {axis_dir[0]}"
            ] = axis_dir_results

        end_time = time.time()
        total_time = (end_time - start_time) / 60

        x_range = abs(
            rom_json["positive x"]["final_position"]["x"]
            - rom_json["negative x"]["final_position"]["x"]
        )
        y_range = abs(
            rom_json["positive y"]["final_position"]["y"]
            - rom_json["negative y"]["final_position"]["y"]
        )
        step_range = [x_range, y_range]

        logger.info(f"Range of motion is {step_range[0]} x {step_range[1]} steps")

        self.calibrated_range = step_range

        return {
            "Time": total_time,
            "CSM Matrix": csm.image_to_stage_displacement_matrix.tolist(),
            "Step Range": step_range,
        }

    def _rom_axis(
        self,
        axis: Literal["x", "y"],
        direction: Literal[1, -1],
        rom_deps: RomDeps,
    ) -> dict:
        """Measure the range of motion in a single axis and direction.

        :param rom_deps: All dependencies that were passed to the calling Action
        :param axis: The axis which is being measured. This must be 'x' or 'y'.
        :param direction: The direction which is being measured. This must be 1 or -1.
        :return: Results dictionary containing stage positions,
           correlations and the final position.
        """
        rom_deps.autofocus.looping_autofocus(dz=1000)

        starting_position = list(rom_deps.stage.position.values())

        rom_data = RomDataTracker()  # initialise data tracking object
        axis_results = {}

        try:
            dir_str = "positive" if direction == 1 else "negative"
            rom_deps.logger.info(
                f"Beginning the {axis}-axis in the {dir_str} direction"
            )

            # Generate required dictionaries for step sizes and minimum offsets
            stream_resolution = [820, 616]
            step_sizes_big = _generate_move_dicts(
                BIG_STEP, stream_resolution, direction
            )

            rom_data.stage_coords.append(rom_deps.stage.position)

            rom_deps.logger.info("Moving the stage in 5 medium sized steps.")
            _acquire_z_predict_points(
                stream_resolution=stream_resolution,
                direction=direction,
                axis=axis,
                data=rom_data,
                rom_deps=rom_deps,
            )

            # 1 big step followed by 3 small steps

            minimum_offset_small = _generate_move_dicts(
                SMALL_STEP, stream_resolution, direction, factor=0.65
            )

            while np.abs(rom_data.delta[axis]) > np.abs(minimum_offset_small[axis]):
                z_diff = _predict_z(
                    positions=rom_data.stage_coords,
                    axis=axis,
                    relative_move=step_sizes_big[axis],
                    stage=rom_deps.stage,
                    csm=rom_deps.csm,
                )

                rom_deps.logger.info("Z calibration complete.")
                rom_deps.stage.move_relative(z=z_diff)
                rom_deps.logger.info(f"Moved in z by {z_diff}")

                # Big step
                if axis == "x":
                    rom_deps.csm.move_in_image_coordinates(x=step_sizes_big["x"], y=0)
                else:
                    rom_deps.csm.move_in_image_coordinates(x=0, y=step_sizes_big["y"])

                rom_deps.autofocus.looping_autofocus(dz=800)
                rom_data.stage_coords.append(rom_deps.stage.position)

                _check_stage_operation(
                    stream_resolution=stream_resolution,
                    direction=direction,
                    axis=axis,
                    data=rom_data,
                    minimum_offset_small=minimum_offset_small,
                    rom_deps=rom_deps,
                )

            # Motion detection
            rom_deps.logger.info("Running motion detection")
            final_pos = _motion_detection(
                axis=axis,
                direction=direction,
                rom_deps=rom_deps,
            )

            rom_data.stage_coords[np.shape(np.array(rom_data.stage_coords))[0] - 1] = (
                final_pos
            )

            axis_results = {
                "correlation_lateral_steps": rom_data.cor_lat_steps.copy(),
                "stage_positions": rom_data.stage_coords.copy(),
                "final_position": final_pos,
            }

        finally:
            rom_deps.stage.move_absolute(
                x=starting_position[0],
                y=starting_position[1],
                z=starting_position[2],
                block_cancellation=True,
            )

        return axis_results
