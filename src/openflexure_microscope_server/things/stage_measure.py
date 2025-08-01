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

import numpy as np
import cv2
from typing import Literal
from PIL import Image
import time
from ..utilities import quadratic
from scipy.optimize import curve_fit
from camera_stage_mapping import fft_image_tracking
import labthings_fastapi as lt
from labthings_fastapi.types.numpy import DenumpifyingDict
import numpy.typing as npt

# Things
from .autofocus import AutofocusThing
from .camera_stage_mapping import CameraStageMapper
from .camera import CameraDependency as CamDep
from .stage import StageDependency as StageDep

CSMDep = lt.deps.direct_thing_client_dependency(
    CameraStageMapper, "/camera_stage_mapping/"
)
AutofocusDep = lt.deps.direct_thing_client_dependency(AutofocusThing, "/autofocus/")


def _generate_move_dicts(
    fov_perc: int,
    stream_resolution: list[int],
    direction: Literal[1, -1],
    factor: float = 1,
) -> dict[str, float]:
    """Create a single dictionary of x and y moves for moving in image coordinates.

    :param fov_perc: The percentage of field of view the stage should move by.
    :param stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :param factor: Multiplicative factor which changes the final result.
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

    :params positions: The list of positions used for predicting z.
    This will usually be a list of all previous positions.
    :params axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :params relative_move: The move which the function is trying to predict z for.
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
    parameters, _ = curve_fit(quadratic, lateral_positions, z_positions)
    z_dest = quadratic(
        stage.position[axis] + (relative_move / pixel_step[axis]), *parameters
    )

    return z_dest - stage.position["z"]


def _move_and_measure(
    step_size: dict[str, float],
    axis: Literal["x", "y"],
    data,
    image1: npt.ArrayLike,
    autofocus_proc: bool,
    csm: CSMDep,
    autofocus: AutofocusDep,
    cam: CamDep,
) -> tuple[npt.ArrayLike, str]:
    """Move the stage and measure the offset between the two positions.

    :params step_size: A dictionary with keys 'x' and 'y' with pixel distances.
    :params axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :params data: The object used to track stage coordinates, correlation and delta.
    :params image1: An image taken before moving to be correlated with image2.
    :params autofocus_proc: If true, looping.autofocus will be used after the stage moves.
    :param csm: A direct_thing_client dependency for camera stage mapping.
    :param autofocus: A direct_thing_client dependency for autofocus.
    :param camera: A raw_thing_client depeendency for the camera.
    :return: All required data for the next move. This includes the updated delta value and offset.
    Also returns what wrong_axis is i.e. if the direction is 'x', wrong_axis = 'y'.
    """
    if axis == "x":
        csm.move_in_image_coordinates(x=step_size["x"], y=0)
        wrong_axis = "y"
    else:
        csm.move_in_image_coordinates(x=0, y=step_size["y"])
        wrong_axis = "x"
    if autofocus_proc:
        autofocus.looping_autofocus(dz=800)
    image2 = cv2.resize(
        np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
    )
    offset = [
        x * 1
        for x in fft_image_tracking.displacement_between_images(
            image_0=image1, image_1=image2, sigma=10, fractional_threshold=0.1, pad=True
        )
    ]  # Units is pixels
    data.delta["x"] = int(offset[1])
    data.delta["y"] = int(offset[0])

    return offset, wrong_axis

def _acquire_z_predict_points(
    stream_resolution: list[int],
    direction: Literal[1, -1],
    axis: Literal["x", "y"],
    data,
    csm: CSMDep,
    cam: CamDep,
    stage: StageDep,
    autofocus: AutofocusDep,
    logger: lt.deps.InvocationLogger,
) -> None:
    """Complete 5 medium sized steps to collect stage coordinates for prediction.

    :params stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :params axis: The axis which is being measured. This must be 'x' or 'y'.
    :params data: The object used to track stage coordinates, correlation and delta.
    :param csm: A direct_thing_client dependency for camera stage mapping.
    :param camera: A raw_thing_client depeendency for the camera.
    :param stage: A raw_thing_client depeendency for the microscope stage.
    :param autofocus: A direct_thing_client dependency for autofocus.
    :return: Stage_coords and cor_lat_steps are lists of data tracked throughout the test.
    Delta is updated and tracked after each move.
    """
    medium_step = 50
    wrong_axis_max_medium = _generate_move_dicts(
        medium_step, stream_resolution, direction, factor=0.1
    )
    for _loop in range(5):
        image1 = cv2.resize(
            np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
        )  # Captures image with option to resize
        offset, wrong_axis = _move_and_measure(
            step_size=_generate_move_dicts(medium_step, stream_resolution, direction),
            axis=axis,
            data=data,
            image1=image1,
            autofocus_proc=True,
            csm=csm,
            autofocus=autofocus,
            cam=cam,
        )
        logger.info(f"Offset measured as {data.delta[axis]}")

        data.measure(stage.position, offset)

        assert np.abs(data.delta[wrong_axis]) < np.abs(
            wrong_axis_max_medium[wrong_axis]
        )


def _check_stage_operation(
    small_step: int,
    stream_resolution: list[int],
    direction: Literal[1, -1],
    axis: Literal["x", "y"],
    data,
    minimum_offset_small: dict[str, float],
    csm: CSMDep,
    cam: CamDep,
    stage: StageDep,
    autofocus: AutofocusDep,
    logger: lt.deps.InvocationLogger,
) -> None:
    """Carries out 3 small moves in a given direction and axis.

    :params small_step: The integer value used to generate the small step sizes.
    :params stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :params axis: The axis which is being measured. This must be 'x' or 'y'.
    :params data: The object used to track stage coordinates, correlation and delta.
    :params minimum_offset_small: A dictionary containing the minimum values for
    a successful correlation.
    :param csm: A direct_thing_client dependency for camera stage mapping.
    :param camera: A raw_thing_client depeendency for the camera.
    :param stage: A raw_thing_client depeendency for the microscope stage.
    :param autofocus: A direct_thing_client dependency for autofocus.
    :return: Stage_coords and cor_lat_steps are lists of data tracked throughout the test.
    Delta is updated and tracked after each move.
    """
    failure_count = 0

    for _loop in range(3):
        image1 = cv2.resize(
            np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
        )
        offset, wrong_axis = _move_and_measure(
            step_size=_generate_move_dicts(small_step, stream_resolution, direction),
            axis=axis,
            data=data,
            image1=image1,
            autofocus_proc=False,
            csm=csm,
            autofocus=autofocus,
            cam=cam,
        )
        logger.info(f"Offset measured as {data.delta[axis]}")

        # If correlation is too small, refocuses and capture new image 3 times.
        while (
            np.abs(data.delta[axis]) < np.abs(minimum_offset_small[axis])
            and failure_count < 3
        ):
            logger.info(
                f"Correlation failed. Refocusing to check. Attempt {failure_count + 1}/3"
            )
            autofocus.looping_autofocus(dz=1000)
            image2 = cv2.resize(
                np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
            )
            failure_count += 1
            offset = [
                x * 1
                for x in fft_image_tracking.displacement_between_images(
                    image_0=image1,
                    image_1=image2,
                    sigma=10,
                    fractional_threshold=0.1,
                    pad=True,
                )
            ]  # Units is pixels
            data.delta["x"] = int(offset[1])
            data.delta["y"] = int(offset[0])
            logger.info(
                f"Displacement found was {data.delta[axis]}.\
                Minimum offset is {minimum_offset_small[axis]}"
            )

        data.measure(stage.position, offset)

        assert np.abs(data.delta[wrong_axis]) < np.abs(
            _generate_move_dicts(
                small_step,
                stream_resolution,
                direction,
                factor=0.1)[
                wrong_axis
            ]
        )

        # this means the edge has been found
        if np.abs(data.delta[axis]) < np.abs(minimum_offset_small[axis]):
            logger.info("Edge has been found.")
            break


def _motion_detection(
    axis: Literal["x", "y"],
    direction: Literal[1, -1],
    csm: CSMDep,
    stage: StageDep,
    cam: CamDep,
    logger: lt.deps.InvocationLogger,
) -> dict:
    """Move the stage until motion is detected along a specified axis and direction.

    :params axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :params direction: The direction in which the stage was moving
    previous to motion detection being used.
    :param csm: A direct_thing_client dependency for camera stage mapping.
    :param stage: A raw_thing_client depeendency for the microscope stage.
    :param camera: A raw_thing_client depeendency for the camera.
    :return: The stage coordinates where motion was detected.
    """
    displacements = [
        1,
        2,
        4,
        8,
        16,
        32,
        64,
        128,
        256,
        512,
    ]  # Array of increasing pixel sizes
    motion_minimum = 20  # minimum number of pixels for motion to be detected

    this_motion_step = {"x": 0, "y": 0}

    delta = {"x": 0, "y": 0}

    for loop in range(np.shape(displacements)[0]):
        this_motion_step[axis] = displacements[loop] * direction * -1
        logger.info(f"Testing with step size {this_motion_step[axis]}")
        image1 = cv2.resize(
            np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
        )
        csm.move_in_image_coordinates(x=this_motion_step["x"], y=this_motion_step["y"])
        image2 = cv2.resize(
            np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
        )
        offset = [
            x * 1
            for x in fft_image_tracking.displacement_between_images(
                image_0=image1,
                image_1=image2,
                sigma=10,
                fractional_threshold=0.1,
                pad=True,
            )
        ]
        delta["x"] = int(offset[1])
        delta["y"] = int(offset[0])
        logger.info(f"Offset measured as {np.abs(delta[axis])}")
        if np.abs(delta[axis]) > motion_minimum:
            logger.info("Motion detected.")
            break

    return stage.position


class RomDataTracker:
    """Class for tracking range of motion data."""

    def __init__(
        self,
        stage_coords: list[dict[str, int]] = [],
        cor_lat_steps: list[list[float]] = [],
        delta: dict = {"x": 0, "y": 0},
    ):
        """Define useful data tracked throughout test."""
        self.stage_coords = stage_coords
        self.cor_lat_steps = cor_lat_steps
        self.delta = delta

    def measure(self, current_pos: dict[str, int], cor: list[float]):
        """Store useful data."""
        self.stage_coords.append(current_pos)
        self.cor_lat_steps.append(cor)

    def reset_tracker(self):
        """Empty the rom tracker."""
        self.stage_coords.clear()
        self.cor_lat_steps.clear()


class RangeofMotionThing(lt.Thing):
    """A class used to measure the range of motion of the stage in X and Y."""

    def rom_axis(
        self,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CamDep,
        csm: CSMDep,
        logger: lt.deps.InvocationLogger,
        axis: Literal["x", "y"],
        direction: Literal[1, -1],
    ) -> dict:
        """Measure the range of motion in a single axis and direction.

        :param stage: A raw_thing_client depeendency for the microscope stage.
        :param cam: A raw_thing_client depeendency for the camera.
        :param csm: A raw_thing_client depeendency for camera stage mapping.
        :param logger: A raw_thing_client depeendency for the logger.
        :params axis: The axis which is being measured. This must be 'x' or 'y'.
        :params direction: The direction which is being measured. This must be 1 or -1.
        :return: Results dictionary containing stage positions,
        correlations and the final position.
        """
        autofocus.looping_autofocus(dz=1000)

        starting_position = list(stage.position.values())

        rom_data = RomDataTracker()  # initialise data tracking object
        axis_results = {}

        try:
            logger.info(
                f"Beginning the {axis}-axis in the {'positive' if direction == 1 else 'negative'}\
                    direction"
            )

            # Generate required dictionaries for step sizes and minimum offsets
            stream_resolution = [820, 616]
            big_step = 200
            small_step = 20
            step_sizes_big = _generate_move_dicts(
                big_step, stream_resolution, direction
            )

            rom_data.stage_coords.append(stage.position)

            logger.info("Moving the stage in 5 medium sized steps.")
            _acquire_z_predict_points(
                stream_resolution=stream_resolution,
                direction=direction,
                axis=axis,
                data=rom_data,
                csm=csm,
                cam=cam,
                stage=stage,
                autofocus=autofocus,
                logger=logger,
            )

            # 1 big step followed by 3 small steps

            minimum_offset_small = _generate_move_dicts(
                small_step, stream_resolution, direction, factor=0.65
            )

            while np.abs(rom_data.delta[axis]) > np.abs(minimum_offset_small[axis]):
                z_diff = _predict_z(
                    positions=rom_data.stage_coords,
                    axis=axis,
                    relative_move=step_sizes_big[axis],
                    stage=stage,
                    csm=csm,
                )

                logger.info("Z calibration complete.")
                stage.move_relative(z=z_diff)
                logger.info(f"Moved in z by {z_diff}")

                # Big step
                if axis == "x":
                    csm.move_in_image_coordinates(x=step_sizes_big["x"], y=0)
                else:
                    csm.move_in_image_coordinates(x=0, y=step_sizes_big["y"])

                autofocus.looping_autofocus(dz=800)
                rom_data.stage_coords.append(stage.position)

                _check_stage_operation(
                    small_step=small_step,
                    stream_resolution=stream_resolution,
                    direction=direction,
                    axis=axis,
                    data=rom_data,
                    minimum_offset_small=minimum_offset_small,
                    csm=csm,
                    cam=cam,
                    stage=stage,
                    autofocus=autofocus,
                    logger=logger,
                )

            # Motion detection
            logger.info("Running motion detection")
            final_pos = _motion_detection(
                axis=axis,
                direction=direction,
                csm=csm,
                stage=stage,
                cam=cam,
                logger=logger,
            )
            rom_data.stage_coords[np.shape(np.array(rom_data.stage_coords))[0] - 1] = (
                final_pos
            )

            axis_results = {
                "correlation_lateral_steps": rom_data.cor_lat_steps.copy(),
                "stage_positions": rom_data.stage_coords.copy(),
                "final_position": final_pos,
            }

            rom_data.reset_tracker()

        except AssertionError:
            logger.info("Parasitic motion detected.")
        finally:
            stage.move_absolute(
                x=starting_position[0],
                y=starting_position[1],
                z=starting_position[2],
                block_cancellation=True,
            )

        return axis_results

    @lt.thing_action
    def rom_main(
        self,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CamDep,
        csm: CSMDep,
        logger: lt.deps.InvocationLogger,
    ):
        """Measures the range of motion of the stage across the x and y axes.

        :param autofocus: A raw_thing_client dependency for autofocus.
        :param stage: A raw_thing_client depeendency for the microscope stage.
        :param cam: A raw_thing_client depeendency for the camera.
        :param csm: A raw_thing_client depeendency for camera stage mapping.
        :param logger: A raw_thing_client depeendency for the logger.
        :return: Results dictionary separated into keys of each axis and direction.
        """
        logger.info(
            "Using the stage to measure the Range of Motion.\
                    Please ensure you are using a big enough sample."
        )
        start_time = time.time()
        rom_results = {}

        # Loop through all axes and directions.
        for axis_dir in [["x", 1], ["x", -1], ["y", 1], ["y", -1]]:
            axis_dir_results = self.rom_axis(
                autofocus,
                stage,
                cam,
                csm,
                logger,
                axis=axis_dir[0],
                direction=axis_dir[1],
            )
            # Save results from single axis and direction
            rom_results[f"{axis_dir}"] = axis_dir_results

        end_time = time.time()
        total_time = (end_time - start_time) / 60

        x_range = abs(
            rom_results["['x', 1]"]["final_position"]["x"]
            - rom_results["['x', -1]"]["final_position"]["x"]
        )
        y_range = abs(
            rom_results["['y', 1]"]["final_position"]["y"]
            - rom_results["['y', -1]"]["final_position"]["y"]
        )
        step_range = [x_range, y_range]
        logger.info(f"Range of motion is {x_range} X {y_range} steps")

        rom_results["Time"] = total_time
        rom_results["CSM Matrix"] = csm.image_to_stage_displacement_matrix
        rom_results["Step Range"] = step_range

        self.last_calibration = DenumpifyingDict(rom_results).model_dump()

        return rom_results

    last_calibration = lt.ThingSetting(initial_value=None, model=dict, readonly=True)
