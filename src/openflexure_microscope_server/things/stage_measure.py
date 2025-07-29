"""File contains all the functions used to measure the range of motion of the OpenFlexure Microscope translation stage.

The range of motion is measured by first taking 5 'medium' sized steps which gives enough positions to predict future z positions. Next, one 'big' step is taken followed by 3
'small' steps to test that the stage is still moving as expected and has not reached the edge. Once the edge has been found and too account for the possibility that a 'big'
step was take just before the edge was reached, the stage is moved in a sequence of increasing pixel sizes in the opposite direction until motion is detected. This is
position is taken as the true final position.

Throughout the test, parasitic motion(motion in the axis not being measured) is tracked and an error is raised if it exceeds a reasonable amount.
"""

import numpy as np
import cv2
import json
from PIL import Image
import time
from ..utilities import quadratic
from scipy.optimize import curve_fit
from camera_stage_mapping import fft_image_tracking
from labthings_fastapi.thing import Thing
from labthings_fastapi.dependencies.thing import direct_thing_client_dependency
from labthings_fastapi.dependencies.invocation import CancelHook, InvocationLogger
from labthings_fastapi.decorators import thing_action
from labthings_sangaboard import SangaboardThing
from labthings_picamera2.thing import StreamingPiCamera2
from labthings_fastapi.types.numpy import DenumpifyingDict
from openflexure_microscope_server.things.autofocus import AutofocusThing
from openflexure_microscope_server.things.camera_stage_mapping import CameraStageMapper

StageDep = direct_thing_client_dependency(SangaboardThing, "/stage/")
CamDep = direct_thing_client_dependency(StreamingPiCamera2, "/camera/")
CSMDep = direct_thing_client_dependency(CameraStageMapper, "/camera_stage_mapping/")
AutofocusDep = direct_thing_client_dependency(AutofocusThing, "/autofocus/")

def generate_move_dicts(fov_perc: int, stream_resolution: list[int], direction: int, factor: float = 1) -> dict[str, float]:
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
    }


def predict_z(positions: list, axis: str, relative_move: float, stage: StageDep, csm: CSMDep) -> float:
    """Predict the next z position for a move using previous positions.

    :params positions: The list of positions used for predicting z. This will usually be a list of all previuos positions.
    :params axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :params relative_move: The move which the function is trying to predict z for. Here, this is inputted with units of pixels.
    :return: A number of pixels the stage needs to move in z.
    """
    pixel_step = {
        'x':1/csm.image_to_stage_displacement_matrix[0][1],
        'y':1/csm.image_to_stage_displacement_matrix[1][0]
    }

    lateral_positions = [i[axis] for i in positions]
    z_positions = [i['z'] for i in positions]
    parameters, _ = curve_fit(quadratic, lateral_positions,  z_positions)
    z_dest = quadratic(stage.position[axis] + (relative_move/pixel_step[axis]), *parameters)

    return z_dest - stage.position["z"]

def move_and_measure(
        step_size: dict[str, float],
        axis: str, delta: dict[str, int],
        image1, autofocus_proc: bool,
        focus_data: list[float],
        csm: CSMDep,
        autofocus: AutofocusDep,
        cam:CamDep) -> tuple:
    """Move the stage and measure the offset between the two positions.

    :params step_size: A dictionary with keys 'x' and 'y' with pixel distances.
    :params axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :params delta: A dictionary of 'x' and 'y' offsets.
    :params image1: An image taken before moving to be correlated with image2.
    :params autofocus_proc: If true, looping.autofocus will be used after the stage moves.
    :params focus_data: A list of focus data returned by the autofocus procedure.
    :return: All required data for the next move. This includes the updated delta value, offset and focus_data. Also returns what wrong_axis is i.e. if the direction is 'x', wrong_axis = 'y'.
    """
    if axis == 'x':
        csm.move_in_image_coordinates(x = step_size['x'], y = 0)
        wrong_axis = 'y'
    else:
        csm.move_in_image_coordinates(x = 0, y = step_size['y'])
        wrong_axis = 'x'
    if autofocus_proc:
        focus_data = autofocus.looping_autofocus(dz = 800)
    image2 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)
    offset = [x * 1 for x in fft_image_tracking.displacement_between_images(image_0 = image1, image_1 = image2, sigma=10, fractional_threshold=0.1, pad=True)] # Units is pixels
    delta['x'] = int(offset[1])
    delta['y'] = int(offset[0])

    return delta, offset, focus_data, wrong_axis

def medium_moves(
        stream_resolution: list[int],
        direction: int,
        axis: str,
        delta: dict[str,int],
        focus_data: list[float],
        stage_coords: list,
        cor_lat_steps: list,
        csm: CSMDep,
        cam: CamDep,
        stage:StageDep,
        autofocus: AutofocusDep,
        logger: InvocationLogger
        ) -> tuple:
    """Carries out the medium sized steps section of the range of motion test to get 5 points to make z position predictions with.

    :params stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :params axis: The axis which is being measured. This must be 'x' or 'y'.
    :params delta: A dictionary of 'x' and 'y' offsets.
    :params focus_data: A list of focus data returned by the autofocus procedure.
    :params stage_coords: A list of all previous positions the stage has been.
    :params cor_lat_steps: A list of all correlation values.
    :return: Stage_coords and cor_lat_steps are lists of data tracked throughout the test. Delta is updated and tracked after each move.
    """
    medium_step = 50
    wrong_axis_max_medium = generate_move_dicts(
        medium_step, stream_resolution, direction, factor=0.1
    )
    for loop in range(5):
        image1 = cv2.resize(
            np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
        )
        delta, offset, focus_data, wrong_axis = move_and_measure(
            step_size=generate_move_dicts(medium_step, stream_resolution, direction),
            axis=axis,
            delta=delta,
            image1=image1,
            autofocus_proc=True,
            focus_data=focus_data,
            csm=csm,
            autofocus=autofocus,
            cam=cam,
        )
        logger.info(f"Offset measured as {delta[axis]}")
        stage_coords.append(stage.position)
        cor_lat_steps.append(offset)

        assert(np.abs(delta[wrong_axis]) < np.abs(wrong_axis_max_medium[wrong_axis]))
    return stage_coords, cor_lat_steps, delta

def small_moves(
    small_step: int,
    stream_resolution: list[int],
    direction: int,
    axis: str,
    delta: dict[str, int],
    focus_data: list[float],
    stage_coords: list,
    cor_lat_steps: list,
    minimum_offset_small: dict[str, float],
    csm: CSMDep,
    cam: CamDep,
    stage: StageDep,
    autofocus: AutofocusDep,
    logger: InvocationLogger,
) -> tuple:
    """Carries out 3 small moves in a given direction and axis.

    :params small_step: The integer value used to generate the small step sizes.
    :params stream_resolution: The resolution of the stream from the camera.
    :param direction: The direction the stage moves.
    :params axis: The axis which is being measured. This must be 'x' or 'y'.
    :params delta: A dictionary of 'x' and 'y' offsets.
    :params focus_data: A list of focus data returned by the autofocus procedure.
    :params stage_coords: A list of all previous positions the stage has been.
    :params cor_lat_steps: A list of all correlation values.
    :params minimum_offset_small: A dictionary containing the minimum values for a successful correlation.
    :return: Stage_coords and cor_lat_steps are lists of data tracked throughout the test. Delta is updated and tracked after each move.
    """
    failure_count = 0
    wrong_axis_max_small = generate_move_dicts(small_step, stream_resolution, direction, factor=0.1)

    for loop in range(3):
        image1 = cv2.resize(
            np.array(Image.open(cam.grab_jpeg().open())), dsize=(0, 0), fx=1, fy=1
        )
        delta, offset, focus_data, wrong_axis = move_and_measure(
            step_size=generate_move_dicts(small_step, stream_resolution, direction),
            axis=axis,
            delta=delta,
            image1=image1,
            autofocus_proc=False,
            focus_data=focus_data,
            csm=csm,
            autofocus=autofocus,
            cam=cam,
        )
        logger.info(f"Offset measured as {delta[axis]}")

        while (
            np.abs(delta[axis]) < np.abs(minimum_offset_small[axis])
            and failure_count < 3
        ):
            logger.info(
                f"Correlation failed. Refocusing to check. Attempt {failure_count + 1}/3"
            )
            focus_data = autofocus.looping_autofocus(dz=1000)
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
            delta["x"] = int(offset[1])
            delta["y"] = int(offset[0])
            logger.info(
                f"Displacement found was {delta[axis]}. Minimum offset is {minimum_offset_small[axis]}"
            )

        stage_coords.append(stage.position)
        cor_lat_steps.append(offset)

        assert np.abs(delta[wrong_axis]) < np.abs(wrong_axis_max_small[wrong_axis])

        if np.abs(delta[axis]) < np.abs(minimum_offset_small[axis]):  # this means the edge has been found
            logger.info("Edge has been found.")
            break
    return stage_coords, cor_lat_steps, delta

def motion_detection(axis: str, direction: int, csm: CSMDep, stage: StageDep, cam: CamDep, logger: InvocationLogger) -> dict:
    """Move the stage until motion is detected along a specified axis and direction.

    :params axis: The axis in which the stage is moving. This must be 'x' or 'y'.
    :params direction: The direction in which the stage was moving previous to motion detection being used.
    :return: The stage coordinates where motion was detected.
    """
    displacements = [1,2,4,8,16,32,64,128,256,512]  # Array of increasing step sizes
    motion_minimum = 20  # minimum nuber of pixels for motion to be detected

    this_motion_step = {
        'x': 0,
        'y': 0
    }

    delta = {
        'x': 0,
        'y': 0
    }

    for loop in range(np.shape(displacements)[0]):
        this_motion_step[axis] = displacements[loop] * direction * -1
        logger.info(f"Testing with step size {this_motion_step[axis]}")
        image1 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)
        csm.move_in_image_coordinates(x = this_motion_step['x'], y = this_motion_step['y'])
        image2 = cv2.resize(np.array(Image.open(cam.grab_jpeg().open())), dsize=(0,0), fx= 1, fy= 1)
        offset = [x * 1 for x in fft_image_tracking.displacement_between_images(
            image_0 = image1, image_1 = image2, sigma=10, fractional_threshold=0.1, pad=True)] # Units is pixels
        delta['x'] = int(offset[1])
        delta['y'] = int(offset[0])
        logger.info(f"Offset measured as {np.abs(delta[axis])}")
        if np.abs(delta[axis]) > motion_minimum:
            logger.info("Motion detected.")
            break

    return stage.position

class RangeofMotionThing(Thing):
    """A class used to measure the range of motion of the stage in X and Y."""

    def rom_axis(
        self,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CamDep,
        csm: CSMDep,
        logger: InvocationLogger,
        axis: str,
        direction: int
    ) -> dict:
        """Measure the range of motion in a single axis and direction.

        :params axis: The axis which is being measured. This must be 'x' or 'y'.
        :params direction: The direction which is being measured. This must be 1 or -1.
        :return: Results dictionary containing stage positions, correlations and the final position.
        """
        focus_data = autofocus.looping_autofocus(dz = 1000)

        starting_position = list(stage.position.values())

        stage_coords = []
        cor_lat_steps = []
        axis_results = {}

        try:
            if direction == 1:
                dir_word = "positive"
            else:
                dir_word = "negative"

            logger.info(f"Beginning the {axis}-axis in the {dir_word} direction")

            # Generate required dictionaries for step sizes and minimum offsets
            stream_resolution = cam.stream_resolution

            big_step = 200
            small_step = 20
            step_sizes_big = generate_move_dicts(big_step, stream_resolution, direction)

            delta = {
                'x':0,
                'y':0
            }

            stage_coords.append(stage.position)

            logger.info("Moving the stage in 5 medium sized steps.")

            stage_coords, cor_lat_steps, delta = medium_moves(
                stream_resolution=stream_resolution,
                direction=direction,
                axis=axis,
                delta=delta,
                focus_data=focus_data,
                stage_coords=stage_coords,
                cor_lat_steps=cor_lat_steps,
                csm=csm,
                cam=cam,
                stage=stage,
                autofocus=autofocus,
                logger=logger,
            )

            # 1 big step followed by 3 small steps

            minimum_offset_small = generate_move_dicts(
                small_step, stream_resolution, direction, factor=0.65
            )

            while np.abs(delta[axis]) > np.abs(minimum_offset_small[axis]):
                z_diff = predict_z(positions = stage_coords, axis = axis, relative_move = step_sizes_big[axis], stage = stage, csm = csm)

                logger.info("Z calibration complete.")

                stage.move_relative(z = z_diff)

                logger.info(f"Moved in z by {z_diff}")

                if axis == 'x':
                    csm.move_in_image_coordinates(x = step_sizes_big['x'], y = 0)
                else:
                    csm.move_in_image_coordinates(x = 0, y = step_sizes_big['y'])

                focus_data = autofocus.looping_autofocus(dz = 800)

                stage_coords.append(stage.position)

                stage_coords, cor_lat_steps, delta = small_moves(
                    small_step=small_step,
                    stream_resolution=stream_resolution,
                    direction=direction,
                    axis=axis,
                    delta=delta,
                    focus_data=focus_data,
                    stage_coords=stage_coords,
                    cor_lat_steps=cor_lat_steps,
                    minimum_offset_small=minimum_offset_small,
                    csm=csm,
                    cam=cam,
                    stage=stage,
                    autofocus=autofocus,
                    logger=logger,
                )

            # Motion detection
            logger.info("Running motion detection")

            final_pos = motion_detection(axis = axis, direction = direction, csm = csm, stage = stage, cam = cam, logger = logger)

            stage_coords[np.shape(stage_coords)[0] - 1] = final_pos

            axis_results = {
                "correlation_lateral_steps": cor_lat_steps,
                "stage_positions": stage_coords,
                "final_position": final_pos
            }
        except AssertionError:
            logger.info("Parasitic motion detected.")
        finally:
            stage.move_absolute(x = starting_position[0], y = starting_position[1], z = starting_position[2], block_cancellation=True)

        return axis_results

    @thing_action
    def rom_main(
        self,
        autofocus: AutofocusDep,
        stage: StageDep,
        cam: CamDep,
        csm: CSMDep,
        cancel: CancelHook,
        logger: InvocationLogger
    ):
        """Measures the range of motion of the stage across the x and y axes.

        :return: Results dictionary separated into keys of each axis and direction.
        """
        logger.info("Using the stage to measure the Range of Motion. Please ensure you are using a big enough sample.")
        start_time = time.time()
        rom_results = {}

        for axis_dir in [['x', 1],['x', -1],['y', 1],['y', -1]]:
            axis_dir_results = self.rom_axis(
                autofocus,
                stage,
                cam,
                csm,
                cancel,
                logger,
                axis = axis_dir[0],
                direction = axis_dir[1]
                )
            rom_results[f"{axis_dir}"] = axis_dir_results

        end_time = time.time()
        total_time = (end_time - start_time)/60

        x_range = abs(rom_results["['x', 1]"]["final_position"]["x"] - rom_results["['x', -1]"]["final_position"]["x"])
        y_range = abs(rom_results["['y', 1]"]["final_position"]["y"] - rom_results["['y', -1]"]["final_position"]["y"])

        step_range = [x_range, y_range]

        logger.info(f"Range of motion is {x_range} X {y_range}")

        rom_results["Time"] = total_time
        rom_results["CSM Matrix"] = csm.image_to_stage_displacement_matrix
        rom_results["Step Range"] = step_range

        self.thing_settings["rom_data"] = DenumpifyingDict(rom_results).model_dump()

        with open("/var/openflexure/ROM_Test_Results.json", 'w') as file_object:
            json.dump(rom_results, file_object, indent = 3)

        return rom_results

