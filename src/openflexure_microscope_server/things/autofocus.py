"""OpenFlexure Microscope autofocus module.

This module defines a Thing that is responsible for using the stage and
camera together to perform an autofocus routine, and for collecting stacks
of images (a 'z-stack').

See repository root for licensing information.
"""

import enum
import logging
import os
import time
from dataclasses import dataclass
from types import TracebackType
from typing import Literal, Mapping, Optional, Self, Sequence

import numpy as np
from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

import labthings_fastapi as lt
from labthings_fastapi.types.numpy import NDArray

from .camera import BaseCamera, CaptureParams
from .stage import BacklashCompensation, BaseStage

LOGGER = logging.getLogger(__name__)
MIN_TEST_IMAGE_COUNT = 3
MAX_TEST_IMAGE_COUNT = 9
EXTRA_STACK_CAPTURES = 15


class NotStreamingError(RuntimeError):
    """No images captured from stream. The camera is almost certainly not streaming."""


class SharpnessMethod(enum.Enum):
    """The possible SharpnessMethods for autofocus."""

    JPEG = enum.auto()


class AutofocusParams(BaseModel):
    """A class for running autofocus routines."""

    dz: int
    sharpness_method: SharpnessMethod = SharpnessMethod.JPEG


class StackOrigin(enum.Enum):
    """The position of the current location in the stack."""

    START = enum.auto()
    CENTER = enum.auto()
    END = enum.auto()


class StackParams(BaseModel):
    """A class for holding stack parameters, and returning computed ones."""

    stack_dz: int
    images_to_save: int = Field(gt=0)

    # Using docstrings under variables as this is how pdoc would expect
    # attributed to be documented

    settling_time: float = Field(default=0.3, ge=0)
    """Time (in seconds) between moving and capturing an image"""

    origin: StackOrigin = StackOrigin.START
    """Where the stack is positioned relative to the current z position."""


class SmartStackParams(StackParams):
    """A class for holding smart stack parameters, and returning computed ones."""

    min_images_to_test: int

    save_on_failure: bool = False
    """Whether to save an image even if no focus was found."""

    check_turning_points: bool = True
    """
    Whether to check the number of turning points in
    the sharpnesses of the images in the stack is exactly 1.
    (May fail with thick samples)
    """

    stack_height_limit: int = 15
    """
    How many images can be appended to the stack after the predicted peak to test
    for focus before assuming the focus was passed, and restarting the stack
    """

    img_undershoot: int = 5
    """
    How far below (in factors of stack_dz) the estimated optimal starting position to
    begin the stack. Better to start slightly too low and require many images, rather
    than too high and needing to autofocus and restart the stack
    """

    max_attempts: int = 3
    """Maximum number of times to attempt fast stack"""

    @field_validator("min_images_to_test")
    @classmethod
    def check_images_to_test(cls, min_images_to_test: int) -> int:
        """Verify that the images to test parameter matches various constraints."""
        if min_images_to_test < MIN_TEST_IMAGE_COUNT:
            raise ValueError(
                f"Can't test for focus with fewer than {MIN_TEST_IMAGE_COUNT} images."
            )
        if min_images_to_test > MAX_TEST_IMAGE_COUNT:
            raise ValueError(
                f"Testing with more than {MAX_TEST_IMAGE_COUNT} images is likely to "
                "focus on the cover slip, or strike the sample."
            )
        if min_images_to_test % 2 == 0 or min_images_to_test <= 0:
            raise ValueError(
                "Minimum number of images to test should be positive and odd"
            )
        return min_images_to_test

    @field_validator("images_to_save")
    @classmethod
    def check_images_to_save(cls, images_to_save: int) -> int:
        """Verify that the images to save parameter is positive and odd."""
        if images_to_save % 2 == 0 or images_to_save <= 0:
            raise ValueError("Images to save must be positive and odd")
        return images_to_save

    @model_validator(mode="after")
    def check_image_limits(self) -> "SmartStackParams":
        """Ensure the number of images to save isn't more than the minimum tested."""
        if self.images_to_save > self.min_images_to_test:
            raise ValueError("Can't save more images than the minimum number tested.")
        return self

    # Note MyPy doesn't support decorating properties. See MyPy Pull #16571 and issue #14461.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def stack_z_range(self) -> int:
        """The range of the z stack, in steps.

        Note that this is the range of the minimum number of images captured,
        which is also the range of the images stored in memory that can be
        saved.
        """
        return self.stack_dz * (self.min_images_to_test - 1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def steps_undershoot(self) -> int:
        """The distance to deliberately undershoot the estimated optimal starting point."""
        # Starting too low by "steps_undershoot" makes smart stacking faster.
        # Starting a stack too high requires it to move to the start,
        # autofocus and then re-stack. Starting slightly too low only
        # requires extra +z movements and captures.
        return self.stack_dz * self.img_undershoot

    @computed_field  # type: ignore[prop-decorator]
    @property
    def max_images_to_test(self) -> int:
        """The maximum number of images that will be captured and tested in a stack.

        This is 15 images more then the minimum number that are captured.
        """
        return self.min_images_to_test + EXTRA_STACK_CAPTURES

    def slice_to_save(self, sharpest_index: int) -> slice:
        """Return the slice of images to save given the index of the sharpest image."""
        images_each_side = (self.images_to_save - 1) // 2
        return slice(
            max(sharpest_index - images_each_side, 0),
            sharpest_index + images_each_side + 1,
        )


@dataclass
class CaptureInfo:
    """The information from a capture in a smart_z_stack."""

    buffer_id: int
    position: Mapping[str, int]
    sharpness: int

    @property
    def filename(self) -> str:
        """The filename for this image generated from the position.

        The file name is in the format ``img_{x}_{y}_{z}`` where x, y, and z are the
        positions from the microscope stage.
        """
        return (
            f"img_{self.position['x']}_{self.position['y']}_{self.position['z']}.jpeg"
        )


def _get_capture_by_id(captures: list[CaptureInfo], buffer_id: int) -> CaptureInfo:
    """Return the capture from a list of CaptureInfo objects with the matching id.

    :param captures: A list of capture objects
    :param buffer_id: The buffer id of the image to return

    :returns: the CaptureInfo object of the capture with matching id

    :raises ValueError: if buffer_id does not match the buffer_id of any captures
    """
    return captures[_get_capture_index_by_id(captures, buffer_id)]


def _get_capture_index_by_id(captures: list[CaptureInfo], buffer_id: int) -> int:
    """Return the index of the capture with the matching id.

    :param captures: A list of capture objects
    :param buffer_id: The buffer id of the image to return

    :returns: the list index of the capture with matching id

    :raises ValueError: if buffer_id does not match the buffer_id of any captures
    """
    ids = [capture.buffer_id for capture in captures]
    if buffer_id not in ids:
        raise ValueError(f"No capture has a buffer id of {buffer_id}")
    return ids.index(buffer_id)


class SharpnessDataArrays(BaseModel):
    """A BaseModel with the position and sharpness data from JPEGSharpnessMonitor.

    Each JPEG Size (representing a sharpness metric) has an associated timestamp,
    as does each stage position. The stage positions need to be interpolated so
    they correspond with the image timestamps.
    """

    jpeg_times: NDArray
    jpeg_sizes: NDArray
    stage_times: NDArray
    stage_positions: list[dict[str, int]]


class JPEGSharpnessMonitor:
    """A class with direct access to the CameraThing for monitoring the MJPEG stream.

    The autofocus algorithm uses sharpness calculated from the file size of the
    images in the MJPEG stream. This class monitors both the stage position and the
    jpeg sharpness over time.

    The ``run`` context manager is used to start monitoring the camera stream. Position
    monitoring happens during ``focus_rel``. Raw data can be retrieved with
    ``data_dict`` and data with interpolated ``z`` positions can be retrieved with
    move_data.

    """

    def __init__(self, stage: BaseStage, camera: BaseCamera) -> None:
        """Initialise a new JPEGSharpnessMonitor. The args are injected automatically.

        :param stage: A direct_thing_client dependency for the the microscope stage.
        :param camera: A raw_thing_client depeendency for the camera. This is a raw
            dependency as the underlying class needs to be
        """
        self.camera = camera
        self.stage = stage
        LOGGER.debug(f"Created sharpness monitor with {stage}, {camera}")
        self.stage_positions: list[Mapping[str, int]] = []
        self.stage_times: list[float] = []
        self.jpeg_times: list[float] = []
        self.jpeg_sizes: list[int] = []

    running = False

    async def monitor_sharpness(self) -> None:
        """Start monitoring the frame sizes."""
        self.running = True
        async for frame in self.camera.lores_mjpeg_stream.frame_async_generator():
            self.jpeg_times.append(time.time())
            self.jpeg_sizes.append(len(frame))
            if not self.running:
                break

    def __enter__(self) -> Self:
        """Start context manager, during which sharpness from the camera is monitored."""
        # Use the cameras _thing_server_interface to get access to the server event loop
        # and start a task.
        self.camera._thing_server_interface.start_async_task_soon(
            self.monitor_sharpness
        )
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException],
        _exc_value: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ) -> None:
        """Clean up after context manager is closed."""
        self.running = False

    def focus_rel(self, dz: int, block_cancellation: bool = False) -> tuple[int, int]:
        """Move the stage by dz, monitoring the position over time.

        This performs exactly one move. Multiple calls of this method
        will append to the internal position storage for more complex
        autofocus procedures.

        This should be run from within the JPEGSharpnessMonitor.run
        context manager so that sharpness data and timestamps are also
        collected.
        """
        # Store the start time and position
        self.stage_times.append(time.time())
        self.stage_positions.append(self.stage.position)

        # Main move
        self.stage.move_relative(z=dz, block_cancellation=block_cancellation)

        # Store the end time and position
        self.stage_times.append(time.time())
        self.stage_positions.append(self.stage.position)

        # Index of the data for this movement
        data_index: int = len(self.stage_positions) - 2
        # Final z position after move
        final_z_position: int = self.stage_positions[-1]["z"]
        return data_index, final_z_position

    def move_data(
        self, istart: int, istop: Optional[int] = None
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extract sharpness as a function of (interpolated) z."""
        if istop is None:
            istop = istart + 2
        jpeg_times: np.ndarray = np.array(self.jpeg_times)
        jpeg_sizes: np.ndarray = np.array(self.jpeg_sizes)
        stage_times: np.ndarray = np.array(self.stage_times)[istart:istop]
        stage_heights: np.ndarray = np.array(
            [p["z"] for p in self.stage_positions[istart:istop]]
        )
        try:
            start: int = int(np.argmax(jpeg_times > stage_times[0]))
            stop: int = int(np.argmax(jpeg_times > stage_times[1]))
        except ValueError as e:
            if np.sum(jpeg_times > stage_times[0]) == 0:
                errmsg = (
                    "No images were captured during the move of the stage. "
                    "Perhaps the camera is not streaming images?"
                )
                raise ValueError(errmsg) from e
            raise e
        if stop < 1:
            stop = len(jpeg_times)
            LOGGER.debug("changing stop to %s", (stop))
        jpeg_times = jpeg_times[start:stop]
        jpeg_heights: np.ndarray = np.interp(jpeg_times, stage_times, stage_heights)
        return jpeg_times, jpeg_heights, jpeg_sizes[start:stop]

    def sharpest_z_on_move(self, data_index: int) -> int:
        """Return the z position of the sharpest image on a given move."""
        _, jpeg_heights, jpeg_sizes = self.move_data(data_index)
        if len(jpeg_sizes) == 0:
            raise NotStreamingError(
                "No images were captured during the move of the stage. "
                "Perhaps the camera is not streaming images?"
            )
        return jpeg_heights[np.argmax(jpeg_sizes)]

    def data_dict(self) -> SharpnessDataArrays:
        """Return the gathered data as a single convenient dictionary."""
        data = {}
        for k in ["jpeg_times", "jpeg_sizes", "stage_times", "stage_positions"]:
            data[k] = getattr(self, k)
        return SharpnessDataArrays(**data)


class AutofocusThing(lt.Thing):
    """The Thing concerned with combinations of z axis movements and the camera.

    Actions here involve moving a stage in z, and using the camera to either
    capture images (generally, z-stacking) and measuring the sharpness of the
    field of view to assess focus (autofocus and testing the success of a z-stack)
    """

    _cam: BaseCamera = lt.thing_slot()
    _stage: BaseStage = lt.thing_slot()

    @lt.action
    def fast_autofocus(
        self,
        dz: int = 2000,
        start: Literal["centre", "base"] = "centre",
    ) -> SharpnessDataArrays:
        """Sweep the stage up and down, then move to the sharpest point.

        This method will will move down by dz/2, sweep up by dz, and then evaluate
        the position where the image was sharpest. We'll then move back down, and
        finally up to the sharpest point.
        """
        with JPEGSharpnessMonitor(self._stage, self._cam) as sharpness_monitor:
            # Move to (-dz / 2)
            if start == "centre":
                sharpness_monitor.focus_rel(-dz // 2)
            # Move to dz while monitoring sharpness
            # focus_data_index: Sharpness monitor index for this move
            focus_data_index, _z = sharpness_monitor.focus_rel(
                dz, block_cancellation=True
            )
            # Get the z position with highest sharpness from the previous move
            peak_z: int = sharpness_monitor.sharpest_z_on_move(focus_data_index)
            # Move all the way to the start so it's consistent
            _index, base_z = sharpness_monitor.focus_rel(-dz)
            # Move to the target position fz (relative move of (peak - current z))
            sharpness_monitor.focus_rel(peak_z - base_z)
            # Return all focus data
            return sharpness_monitor.data_dict()

    @lt.action
    def z_move_and_measure_sharpness(
        self,
        dz: Sequence[int],
        wait: float = 0,
    ) -> SharpnessDataArrays:
        """Make a move (or a series of moves) and monitor sharpness.

        This method will will make a series of relative moves in z, and
        return the sharpness (JPEG size) vs time, along with timestamps
        for the moves. This can be used to calibrate autofocus.

        Each move is relative to the last one, i.e. we will finish at
        ``sum(dz)`` relative to the starting position.

        If ``wait`` is specified, we will wait for that many seconds
        between moves.
        """
        with JPEGSharpnessMonitor(self._stage, self._cam) as sharpness_monitor:
            for move_index, current_dz in enumerate(dz):
                if move_index > 0 and wait > 0:
                    time.sleep(wait)
                sharpness_monitor.focus_rel(current_dz)
            return sharpness_monitor.data_dict()

    @lt.action
    def looping_autofocus(
        self,
        dz: int = 2000,
        start: Literal["centre", "base"] = "centre",
    ) -> tuple[list[float], list[float]]:
        """Repeatedly autofocus the stage until it looks focused.

        This action will run the ``fast_autofocus`` action until it settles on a point
        in the middle 3/5 of its range. Such logic can be helpful if the microscope
        is close to focus, but not quite within ``dz/2``. It will attempt to autofocus
        up to 10 times.
        """
        attempt = 0

        with JPEGSharpnessMonitor(self._stage, self._cam) as sharpness_monitor:
            while attempt < 10:
                attempt += 1
                if start == "centre":
                    self._stage.move_relative(
                        x=0,
                        y=0,
                        z=-int(dz / 2),
                        backlash_compensation=BacklashCompensation.Z_ONLY,
                    )

                # Always start centrally for future runs
                start = "centre"

                focus_data_index, _ = sharpness_monitor.focus_rel(
                    dz, block_cancellation=True
                )
                _times, heights, sizes = sharpness_monitor.move_data(focus_data_index)

                peak_height = heights[np.argmax(sizes)]
                target_min = np.min(heights) + dz / 5
                target_max = np.max(heights) - dz / 5

                # move to the peak
                self._stage.move_absolute(
                    z=peak_height,
                    backlash_compensation=BacklashCompensation.Z_ONLY,
                )

                if target_min < peak_height < target_max:
                    # If it is within the target range then return
                    return heights.tolist(), sizes.tolist()
        raise NoFocusFoundError(
            "Looping autofocus couldn't converge on a focus location."
        )

    @lt.action
    def run_smart_stack(
        self,
        stack_parameters: SmartStackParams,
        capture_parameters: CaptureParams,
        autofocus_parameters: AutofocusParams,
    ) -> tuple[bool, int]:
        """Run a smart stack.

        A smart stack captures images offset in z, testing whether the sharpest image
        is towards the centre of the stack.

        The sharpest image, and optionally images around the sharpest, will be saved
        to the images_dir with their coordinates in the filename.

        :param stack_parameters: A SmartStackParams object containing the required
            parameters to run a stack.

        :returns: A tuple containing:

            * A boolean, True if stack was successfully
            * The z position of the sharpest image
        """
        attempt = 0
        while True:
            attempt += 1
            success, captures, sharpest_id = self.smart_z_stack(
                stack_parameters=stack_parameters,
                check_turning_points=stack_parameters.check_turning_points,
            )

            if success or attempt >= stack_parameters.max_attempts:
                break

            # The z position of the first images in the previous attempt.
            initial_z_pos = captures[0].position["z"]
            # If a stack is not successful, move to the start and autofocus
            try:
                self.reset_stack(initial_z_pos, autofocus_parameters.dz)
            except NoFocusFoundError:
                break

        # Save stack_parameters.image_to_save images centred on the sharpest capture.
        # If the smart_stack failed the exact number of images saved may not be
        # stack_parameters.image_to_save
        if success or stack_parameters.save_on_failure:
            self.save_stack(
                sharpest_id=sharpest_id,
                captures=captures,
                stack_parameters=stack_parameters,
                capture_parameters=capture_parameters,
            )

        return success, _get_capture_by_id(captures, sharpest_id).position["z"]

    def reset_stack(
        self,
        initial_z_pos: int,
        autofocus_dz: int,
    ) -> None:
        """Return to the initial z position and run a looping autofocus.

        :param initial_z_pos: The initial z positions of previous captures
        :param  autofocus_dz: the range in steps to autofocus

        ``stage`` and ``sharpness_monitor`` are Thing dependencies passed through
        from the calling action.
        """
        self._stage.move_absolute(z=initial_z_pos)
        self.looping_autofocus(dz=autofocus_dz)

    def save_stack(
        self,
        sharpest_id: int,
        captures: list[CaptureInfo],
        stack_parameters: SmartStackParams,
        capture_parameters: CaptureParams,
    ) -> int:
        """Save the required captures to disk.

        This will save the sharpest image, and optionally extra images either
        side of focus (see ``stack_parameters.images_to_save``).

        :param sharpest_id: the buffer id index of the sharpest image
        :param captures: a list of captures, including file name, image data and
            metadata
        :param stack_parameters: a SmartStackParams object holding stack parameters
        """
        sharpest_index = _get_capture_index_by_id(captures, sharpest_id)
        slice_to_save = stack_parameters.slice_to_save(sharpest_index)

        # Loop through the range, saving each capture to disk
        for capture in captures[slice_to_save]:
            self._cam.save_from_memory(
                jpeg_path=os.path.join(capture_parameters.images_dir, capture.filename),
                save_resolution=capture_parameters.save_resolution,
                buffer_id=capture.buffer_id,
            )
        self._cam.clear_buffers()
        return sharpest_index

    def smart_z_stack(
        self,
        stack_parameters: SmartStackParams,
        check_turning_points: bool,
    ) -> tuple[bool, list[CaptureInfo], int]:
        """Capture a series of images checking that sharpest image central.

        This is part of run_smart_stack. This is the actual z_stackng stacking method
        called by the action run_smart_stack. The action also handles resetting,
        autofocussing, and retrying.

        The images are separated in z offset by stack_parameters.stack_dz, as they
        are captured the last stack_parameters.min_images_to_test images are checked
        to see if the sharpest image is central enough in the stack. If it is the stack
        completes.

        :param stack_parameters: a SmartStackParams object holding stack parameters
        :param check_turning_points: Whether to check the number of turning points in
            the sharpnesses of the images in the stack is exactly 1. (May fail with
            thick samples)

        :returns: A tuple of

            * the stack result (True for successful stack, False for failed stack),
            * a list of CaptureInfo objects,
            * the buffer_id of the sharpest image
        """
        # Move down by the height of the z stack, plus an overshoot
        # Better to start too low and take too many images than too high and need to refocus
        self._stage.move_relative(
            z=-int(
                stack_parameters.steps_undershoot + stack_parameters.stack_z_range / 2
            ),
            backlash_compensation=BacklashCompensation.Z_ONLY,
        )

        captures: list[CaptureInfo] = []
        # Always check for focus using the the last `min_images_to_test` in the
        # stack so check is fair
        ims_to_check = slice(-stack_parameters.min_images_to_test, None)

        # If the sharpest image isn't found within the maximum number of images
        # end the loop and return False indicating the stack failed.
        while len(captures) < stack_parameters.max_images_to_test:
            time.sleep(stack_parameters.settling_time)

            # Append a new image to the stack
            captures.append(
                self.capture_stack_image(buffer_max=stack_parameters.min_images_to_test)
            )

            # If the number of images is enough to test, test them
            if len(captures) >= stack_parameters.min_images_to_test:
                result, capture_id = self.check_stack_result(
                    captures[ims_to_check], check_turning_points=check_turning_points
                )

                if result == "success":
                    return True, captures, capture_id

                if result == "restart":
                    return False, captures, capture_id
                # If reached here the result was "continue"
            self._stage.move_relative(z=stack_parameters.stack_dz)
        return False, captures, capture_id

    def capture_stack_image(self, buffer_max: int) -> CaptureInfo:
        """Capture another image and return the capture information.

        The capture is stored by the camera Thing, and can be saved by ID.

        :param buffer_max: The maximum number of images to tell the camera to keep in memory
            for saving once the stack is complete

        :returns: A CaptureInfo object containing the capture information including its
            camera buffer_id needed for saving.
        """
        stage_location = self._stage.position
        buffer_id = self._cam.capture_to_memory(buffer_max=buffer_max)
        return CaptureInfo(
            buffer_id=buffer_id,
            position=stage_location,
            sharpness=self._cam.grab_jpeg_size(stream_name="lores"),
        )

    # Silence too many returns in this situation as refactoring to reduce returns is
    # unlikely to improve readability. This function is basically a complex switch
    # statement, having an explicit return after each option is clear.
    def check_stack_result(  # noqa: PLR0911
        self, captures: list[CaptureInfo], check_turning_points: bool
    ) -> tuple[Literal["success", "continue", "restart"], int]:
        """Check if the sharpest image in a list of captures is central enough.

        :param captures: a list of the capture objects to for testing if the
            sharpness has converged in the centre
        :param check_turning_points: Whether to check the number of turning points in
            the sharpnesses of the images in the stack is exactly 1. (May fail with
            thick samples)

        :returns: A tuple with two values:

            * result - which is one of three literal values:

                * ``success`` if the sharpest image is towards the centre
                * ``continue`` if the sharpest image is in the final two images of the
                    list
                * ``restart`` if the sharpest image is in the first two images of the
                    list

            * capture_id - the buffer id of the sharpest image
        """
        sharpnesses = np.array([capture.sharpness for capture in captures])
        sharpest_index = np.argmax(sharpnesses)
        # The buffer id of the sharpest image
        capture_id = captures[sharpest_index].buffer_id
        n_imgs = len(captures)

        # If only testing one image, then by definition the sharpest is central
        if n_imgs == 1:
            return "success", capture_id
        # If testing three images, test if the centre is the sharpest
        if n_imgs == 3:
            if sharpest_index == 1:
                return "success", capture_id
            if sharpest_index == 0:
                return "restart", capture_id
            return "continue", capture_id

        try:
            turning = _get_peak_turning_point(sharpnesses)
        except NotAPeakError:
            return "continue", capture_id

        # For larger stacks, test if the best image is not within two of the edge of
        # the stack ie for a stack of 7 images, best image must be between 3rd and 5th
        edge_size = 2

        # Check both the peak from fitting and the sharpest image are not at the
        # edge of the stack.
        if turning < edge_size - 0.5 or sharpest_index < edge_size:
            return "restart", capture_id
        if turning > n_imgs - edge_size - 0.5 or sharpest_index >= n_imgs - edge_size:
            return "continue", capture_id

        if check_turning_points:
            turning_points = _count_turning_points(sharpnesses)
            if turning_points > 1:
                return "continue", capture_id

        return "success", capture_id

    @lt.action
    def run_basic_stack(
        self,
        stack_parameters: StackParams,
        capture_parameters: CaptureParams,
    ) -> tuple[int, list[int]]:
        """Capture a simple z-stack with no focus testing or fitting.

        This performs a fixed stack of images spaced by `stack_dz`,
        saving all images captured. No sharpness testing, restart
        logic, or autofocus is performed.

        :param stack_parameters: StackParams defining stack spacing,
            and image count.
        :param capture_parameters: CaptureParams defining save
            resolution, images directory.

        :returns:
            - Final z position
            - List of z positions captured
        """
        captures: list[CaptureInfo] = []
        z_positions: list[int] = []

        total_range = stack_parameters.stack_dz * (stack_parameters.images_to_save - 1)

        # Determine starting offset based on stack origin
        if stack_parameters.origin == StackOrigin.CENTER:
            target_offset = -total_range // 2
        elif stack_parameters.origin == StackOrigin.END:
            target_offset = -total_range
        else:
            target_offset = 0

        self._stage.move_relative(z=target_offset)

        # Capture images_to_save images
        for move_count in range(stack_parameters.images_to_save):
            time.sleep(stack_parameters.settling_time)

            capture = self.capture_stack_image(
                buffer_max=stack_parameters.images_to_save
            )
            captures.append(capture)
            z_positions.append(capture.position["z"])

            # Only move stage if not on the last image
            if move_count < stack_parameters.images_to_save - 1:
                self._stage.move_relative(z=stack_parameters.stack_dz)

        # Save all captures
        for capture in captures:
            self._cam.save_from_memory(
                jpeg_path=os.path.join(
                    capture_parameters.images_dir,
                    capture.filename,
                ),
                save_resolution=capture_parameters.save_resolution,
                buffer_id=capture.buffer_id,
            )

        self._cam.clear_buffers()

        final_z = self._stage.position["z"]
        return final_z, z_positions


class NotAPeakError(lt.exceptions.InvocationError):
    """The data to fit isn't a peak."""


class NoFocusFoundError(lt.exceptions.InvocationError):
    """No focus found during looping Autofocus."""


def _get_peak_turning_point(sharpnesses: np.ndarray) -> float:
    """Get the turning point for a sharpnesses in a z-stack.

    :param sharpnesses: A numpy array of sharpnesses
    :return: The x value of the turning point where x-axis is 0 to N-1 for the N
        sharpness values

    :raise NotAPeakError: If the fit doesn't have a maximum within 95% confidence.
    """
    # Fit the peak
    x = range(len(sharpnesses))
    coeffs, cov = np.polyfit(x, sharpnesses, deg=2, cov=True)
    # a in the equation a*x^2 + bx + c
    a = float(coeffs[0])
    fit_func = np.poly1d(coeffs)

    # find the peaks's x-position
    turning = float(fit_func.deriv().roots[0])
    # sigma_a the standard error of a
    sigma_a = float(np.sqrt(cov[0, 0]))
    # Estimate the upper 95% confidence bound for the x^2 term
    ci_high = a + 2 * sigma_a
    # If the high 95% confindence interval of the peak is not negative then the
    # fit isn't sure if this is a peak or a U shape, so we continue.
    # -1e-9 is used to guard against weird effects for flat and straight data
    if ci_high > -1e-9:
        raise NotAPeakError("Not a peak to within 95% confidence.")
    return turning


def _count_turning_points(sharpnesses: np.ndarray) -> int:
    """Count the number of turing points, after rejecting those from noise."""
    # Also take the difference of neighbouring points to check for turning points
    d_sharpnesses = sharpnesses[1:] - sharpnesses[:-1]
    # Filter out any points that are not prominent
    prominent = abs(d_sharpnesses) / np.mean(abs(d_sharpnesses)) > 0.5
    d_sharpnesses = d_sharpnesses[prominent]
    # count the sign changes
    return int(np.sum(d_sharpnesses[1:] * d_sharpnesses[:-1] < 0))
