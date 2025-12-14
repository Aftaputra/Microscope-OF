"""OpenFlexure Microscope OpenCV Camera.

This module defines a Thing that is responsible for using the stage and
camera together to perform an autofocus routine.

See repository root for licensing information.
"""

from __future__ import annotations

import io
import logging
import time
from threading import Thread
from types import TracebackType
from typing import Literal, Mapping, Optional

import numpy as np
from PIL import Image, ImageFilter

import labthings_fastapi as lt

from openflexure_microscope_server.ui import (
    ActionButton,
    PropertyControl,
    action_button_for,
    property_control_for,
)

from ..stage import BaseStage
from . import ArrayModel, BaseCamera

LOGGER = logging.getLogger(__name__)

# The ratio between "motor" steps and pixels
# higher related to a faster movement
RATIO = (2, 2, 0.2)

# Some colour variation, for bg detect.
BG_COLOR = [220, 215, 217]

# Random Number Generator
RNG = np.random.default_rng()


class SimulatedCamera(BaseCamera):
    """A Thing that simulates a camera for testing."""

    _stage: Optional[BaseStage] = None
    _server: Optional[lt.ThingServer] = None
    _show_sample: bool = True

    def __init__(
        self,
        thing_server_interface: lt.ThingServerInterface,
        shape: tuple[int, int, int] = (616, 820, 3),
        glyph_shape: tuple[int, int, int] = (121, 121, 3),
        canvas_shape: tuple[int, int, int] = (3000, 4000, 3),
        sample_limits: Optional[tuple[int, int]] = (1000, 1500),
        frame_interval: float = 0.1,
    ) -> None:
        """Initialise the simulated with settings for how images are generated.

        :param shape: The shape (size) of the generated image.
        :param glyph_shape: The size randomly positioned glyphs.
        :param canvas_shape: The shape (size) of the canvas generated on initialisation
            that images are cropped from. If this is too large the it uses resources,
            but its size limits the range of motion of the simulation.
        :param sample_limits: The shape of the sample. Outside this range, the
            camera won't generate any blobs, preventing scanning from running
            indefinitely and better demonstrating background detect.
        :param frame_interval: Nominally the time between frames on the MJPEG stream,
            however the rate may be slower due to calculation time for focus.
        """
        super().__init__(thing_server_interface)
        self.shape = shape
        self.glyph_shape = glyph_shape
        self.canvas_shape = canvas_shape
        self.sample_limits = (
            canvas_shape[:2] if sample_limits is None else sample_limits
        )
        self.frame_interval = frame_interval
        self._capture_thread: Optional[Thread] = None
        self._capture_enabled = False
        self.validate_inputs()
        self.generate_sprites()
        self.generate_blobs()
        self.generate_canvas()

    @lt.property
    def calibration_required(self) -> bool:
        """Whether the camera needs calibrating."""
        return not self.background_detector_status.ready

    def validate_inputs(self) -> None:
        """Validate the inputs passed to the simulation, and raises an error if invalid.

        Currently only tests that the sample size is not greater than the canvas size in any dimension.
        """
        # Iterate through elements in both tuples. As strict is False, will use the shorter of the two tuples
        for a, b in zip(self.canvas_shape, self.sample_limits, strict=False):
            if a < b:
                raise ValueError(
                    "Canvas size must be bigger than or equal to canvas size"
                )

    def generate_sprites(self) -> None:
        """Generate sprites to populate the image."""
        sprite_sizes = [10, 21, 36, 40, 50]
        self.sprites = []

        channel_block = np.zeros(self.glyph_shape[0:2])
        x = np.arange(channel_block.shape[0])
        y = np.arange(channel_block.shape[1])
        # 2D grid of radii
        r_coord = np.sqrt(
            (x[:, None] - np.mean(x)) ** 2 + (y[None, :] - np.mean(y)) ** 2
        )

        for sprite_size in sprite_sizes:
            # Mask of where this sprite is
            sprite_mask = r_coord < sprite_size
            # Calculate a sharp edged circle with value varying from 0 in centre to 1
            # at the edge
            sprite_px = r_coord[sprite_mask]
            sprite_px -= np.min(sprite_px)
            sprite_px /= np.max(sprite_px)
            # Create each channel. Note these will be subtracted from the white value.
            sprite_r = channel_block.copy()
            sprite_r[sprite_mask] = 70 * sprite_px
            sprite_g = channel_block.copy()
            sprite_g[sprite_mask] = 200 * sprite_px
            sprite_b = channel_block.copy()
            sprite_b[sprite_mask] = 70 * sprite_px
            # Stack into a negative image of the sprite
            sprite = np.stack([sprite_r, sprite_g, sprite_b], axis=2)
            # Convert to uint8 and append to the list
            self.sprites.append(sprite.astype(np.uint8))

    def generate_blobs(self, n_blobs: int = 1000) -> None:
        """Generate coordinates of blobs and their sizes, centered around (0,0).

        Note that blob density is determined by sample size and n_blobs, and for larger
        samples n_blobs will need increasing to keep a high level of sample coverage per
        field of view.

        :param n_blobs: The number of blobs to generate.
        """
        self.blobs = np.zeros((n_blobs, 3))
        w = np.max(self.glyph_shape)

        self.blobs[:, 0] = RNG.uniform(w // 2, self.sample_limits[1] - w // 2, n_blobs)
        self.blobs[:, 1] = RNG.uniform(w // 2, self.sample_limits[0] - w // 2, n_blobs)
        self.blobs[:, 2] = RNG.choice(len(self.sprites), n_blobs)

    def generate_canvas(self) -> None:
        """Generate a canvas with generated blobs centered at the middle.

        Canvas is int16 so that random noise can be added to simulation image before
        changing to unit8 to stop wrapping.
        """
        self.blank_canvas = np.ones(self.canvas_shape, dtype=np.int16)
        self.blank_canvas[:, :, 0] *= BG_COLOR[0]
        self.blank_canvas[:, :, 1] *= BG_COLOR[1]
        self.blank_canvas[:, :, 2] *= BG_COLOR[2]
        self.canvas = self.blank_canvas.copy()

        for blob_x, blob_y, sprite_index in self.blobs:
            self.draw_sprite_on_canvas(
                self.sprites[int(sprite_index)], int(blob_y), int(blob_x)
            )

        self.canvas[self.canvas < 0] = 0
        self.canvas[self.canvas > 255] = 255

    def draw_sprite_on_canvas(
        self, sprite: np.ndarray, centre_y: int, centre_x: int
    ) -> None:
        """Place one sprite on canvas at given centre coordinates.

        Note that self.canvas is modified in place.

        :param sprite: The sprite array to place on the canvas.
        :param centre_y: The y coordinate to place the centre of the sprite.
        :param centre_x: The x coordinate to place the centre of the sprite.
        """
        canvas_h, canvas_w, _ = self.canvas.shape
        sprite_h, sprite_w, _ = sprite.shape

        # Canvas region containing the sprite
        top = max(centre_y - sprite_h // 2, 0)
        left = max(centre_x - sprite_w // 2, 0)
        bottom = min(centre_y + (sprite_h - sprite_h // 2), canvas_h)
        right = min(centre_x + (sprite_w - sprite_w // 2), canvas_w)

        self.canvas[top:bottom, left:right] -= sprite

    def generate_image(self, pos: tuple[int, int, int]) -> Image:
        """Generate an image with blobs based on supplied coordinates.

        :param pos: a 3-item tuple containing the x,y,z coordinates of the 'stage'
        """
        canvas_width, canvas_height, _ = self.canvas_shape
        image_width, image_height, _ = self.shape
        pos = tuple(x * s for x, s in zip(pos, RATIO, strict=True))
        top_left = (
            int(pos[0]) - image_width // 2 + self.sample_limits[0] // 2,
            int(pos[1]) - image_height // 2 + self.sample_limits[1] // 2,
        )
        # Create index list with modulo rather than slicing to handle wrapping at the
        # canvas edge.
        x_indices = (np.arange(top_left[0], top_left[0] + image_width)) % canvas_width
        y_indices = (np.arange(top_left[1], top_left[1] + image_height)) % canvas_height
        z_indices = np.arange(self.shape[2])
        canvas = self.canvas if self._show_sample else self.blank_canvas
        # Use npx to make each 1d index list 3D
        focused_image = canvas[np.ix_(x_indices, y_indices, z_indices)]

        image = fast_pil_blur(focused_image, sigma=np.abs(pos[2]) / 5)

        if image.shape != self.shape:
            raise ValueError(
                f"Image shape {image.shape} does not match intended shape {self.shape}"
            )

        # Add noise and convert to uint8
        image += RNG.normal(scale=self.noise_level, size=self.shape).astype("int16")
        image[image < 0] = 0
        image[image > 255] = 255
        return Image.fromarray(image.astype("uint8"))

    def attach_to_server(
        self, server: lt.ThingServer, path: str, setting_storage_path: str
    ) -> None:
        """Wrap the attach_to_server method so the server instance can be stored.

        Direct access to the server instance is needed to get the stage position while
        maintaining the same public API as a real camera that doesn't need this access.
        """
        self._server = server
        super().attach_to_server(server, path, setting_storage_path)

    def get_stage_position(self) -> Mapping[str, int]:
        """Return the stage position.

        The simulation camera has access to the stage position so it can generate a
        different image as the stage moves.
        """
        if not self._stage and self._server:
            self._stage = self._server.things["/stage/"]
        return self._stage.instantaneous_position

    def generate_frame(self) -> Image:
        """Generate a frame with blobs based on the stage coordinates."""
        try:
            pos = self.get_stage_position()
        except Exception as e:
            LOGGER.debug(f"Failed to get stage position: {e}")
            pos = {"x": 0, "y": 0, "z": 0}
        return self.generate_image((pos["y"], pos["x"], pos["z"]))

    def __enter__(self) -> None:
        """Start the capture thread when the Thing context manager is opened."""
        self.start_streaming()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException],
        _exc_value: Optional[BaseException],
        _traceback: Optional[TracebackType],
    ) -> None:
        """Close the capture thread when the Thing context manager is closed."""
        if self.stream_active:
            self._capture_enabled = False
            self._capture_thread.join()

    @lt.action
    def start_streaming(
        self, main_resolution: tuple[int, int] = (820, 616), buffer_count: int = 1
    ) -> None:
        """Start the live stream.

        The start_streaming method is used a camera ``Thing`` to begin streaming
        images or to adjust the stream resolution if streaming is already active.

        The simulation camera does not currently support the resolution argument.
        It will always issue a warning that the resolution is not respected.
        If called while already streaming, the warning will be emitted and no other
        action will be taken.

        :param main_resolution: Currently ignored, this argument exists to ensure consistent API across camera Things.
        :param buffer_count: Currently ignored, this argument exists to ensure consistent API across camera Things.
        """
        LOGGER.warning(
            f"Simulation camera doesn't respect {main_resolution=} or {buffer_count=} "
            "arguments."
        )
        if not self.stream_active:
            self._capture_enabled = True
            self._capture_thread = Thread(target=self._capture_frames)
            self._capture_thread.start()

    @lt.property
    def stream_active(self) -> bool:
        """Whether the MJPEG stream is active."""
        if self._capture_enabled and self._capture_thread:
            return self._capture_thread.is_alive()
        return False

    noise_level: float = lt.property(default=2.0)

    def _capture_frames(self) -> None:
        portal = lt.get_blocking_portal(self)
        last_frame_t = time.time()
        while self._capture_enabled:
            wait_time = last_frame_t - time.time() - self.frame_interval
            if wait_time > 0:
                time.sleep(wait_time)
            last_frame_t = time.time()
            try:
                frame = self.generate_frame()
                self.mjpeg_stream.add_frame(_frame2bytes(frame), portal)
                ds_frame = frame.resize((320, 240), resample=Image.NEAREST)
                self.lores_mjpeg_stream.add_frame(_frame2bytes(ds_frame), portal)

            except Exception as e:
                LOGGER.exception(f"Failed to capture frame: {e}, retrying...")

    @lt.action
    def discard_frames(self) -> None:
        """Discard frames so that the next frame captured is fresh.

        There is nothing to do as this is a simulation!
        """

    @lt.action
    def capture_array(
        self,
        stream_name: Literal["main", "full"] = "full",
        wait: Optional[float] = None,
    ) -> ArrayModel:
        """Acquire one image from the camera and return as an array.

        This function will produce a nested list containing an uncompressed RGB image.
        It's likely to be highly inefficient - raw and/or uncompressed captures using
        binary image formats will be added in due course.

        :param stream_name: Currently ignored, this argument exists to ensure consistent API across camera Things.
        :param wait: Currently ignored, this argument exists to ensure consistent API across camera Things.
        """
        if wait is not None:
            LOGGER.warning("Simulation camera has no wait option. Use None.")
        LOGGER.warning(f"Simulation camera camera doesn't respect {stream_name=}")
        return np.array(self.generate_frame())

    def capture_image(
        self,
        stream_name: Literal["main", "lores", "raw"],
        wait: Optional[float] = None,
    ) -> Image:
        """Capture to a PIL image. This is not exposed as a ThingAction.

        It is used for capture to memory.

        :param stream_name: Currently ignored, this argument exists to ensure consistent API across camera Things.
        :param wait: Currently ignored, this argument exists to ensure consistent API across camera Things.
        """
        if wait is not None:
            LOGGER.warning("Simulation camera has no wait option. Use None.")
        LOGGER.warning(f"Simulation camera camera doesn't respect {stream_name=}")
        return self.generate_frame()

    @lt.action
    def full_auto_calibrate(self, portal: lt.deps.BlockingPortal) -> None:
        """Perform a full auto-calibration.

        For the simulation microscope the process is:

        * ``remove_sample``
        * ``set_background``
        * ``load_sample``
        """
        self.remove_sample()
        time.sleep(0.2)
        self.set_background(portal)
        time.sleep(0.2)
        self.load_sample()

    @lt.action
    def remove_sample(self) -> None:
        """Show the simulated background with no sample."""
        if not self._show_sample:
            raise RuntimeError("Sample is already removed.")
        self._show_sample = False

    @lt.action
    def load_sample(self) -> None:
        """Show the simulated sample."""
        if self._show_sample:
            raise RuntimeError("Sample is already in place.")
        self._show_sample = True

    @lt.property
    def primary_calibration_actions(self) -> list[ActionButton]:
        """The calibration actions for both calibration wizard and settings panel."""
        return [
            action_button_for(
                self.full_auto_calibrate, submit_label="Full Auto-Calibrate"
            ),
        ]

    @lt.property
    def secondary_calibration_actions(self) -> list[ActionButton]:
        """The calibration actions that appear only in settings panel."""
        return [
            action_button_for(self.load_sample, submit_label="Load Sample"),
            action_button_for(self.remove_sample, submit_label="Remove Sample"),
        ]

    @lt.property
    def manual_camera_settings(self) -> list[PropertyControl]:
        """The camera settings to expose as property controls in the settings panel."""
        return [property_control_for(self, "noise_level", label="Noise Level")]


def _frame2bytes(frame: Image) -> bytes:
    """Convert frame to bytes."""
    with io.BytesIO() as buf:
        # Save in low quality for speed.
        frame.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def fast_pil_blur(array: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian blur using PIL (faster than scipy)."""
    if sigma < 0.5:
        return array  # no visible blur needed

    img_pil = Image.fromarray(array.astype(np.uint8))
    img_pil = img_pil.filter(ImageFilter.GaussianBlur(radius=sigma))

    # Convert back to NumPy array
    return np.array(img_pil, dtype=array.dtype)
