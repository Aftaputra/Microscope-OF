"""OpenFlexure Microscope OpenCV Camera.

This module defines a Thing that is responsible for using the stage and
camera together to perform an autofocus routine.

See repository root for licensing information.
"""

from __future__ import annotations
import io
import json
import logging
from typing import Literal, Optional
from threading import Thread
import time

import cv2
import numpy as np
import piexif
from scipy.ndimage import gaussian_filter

import labthings_fastapi as lt

from openflexure_microscope_server.ui import ActionButton, action_button_for

from . import BaseCamera, JPEGBlob, ArrayModel
from ..stage import BaseStage

# The ratio between "motor" steps and pixels
# higher related to a faster movement
RATIO = 0.2

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
        shape: tuple[int, int, int] = (600, 800, 3),
        glyph_shape: tuple[int, int, int] = (91, 91, 3),
        canvas_shape: tuple[int, int, int] = (3000, 4000, 3),
        frame_interval: float = 0.1,
    ):
        """Initialise the simulated with settings for how images are generated.

        :param shape: The shape (size) of the generated image.
        :param glyph_shape: The size randomly positioned glyphs.
        :param canvas_shape: The shape (size) of the canvas generated on initialisation
            that images are cropped from. If this is too large the it uses resources,
            but its size limits the range of motion of the simulation.
        :param frame_interval: Nominally the time between frames on the MJPEG stream,
            however the rate may be slower due to calculation time for focus.
        """
        super().__init__()
        self.shape = shape
        self.glyph_shape = glyph_shape
        self.canvas_shape = canvas_shape
        self.frame_interval = frame_interval
        self._capture_thread: Optional[Thread] = None
        self._capture_enabled = False
        self.generate_sprites()
        self.generate_blobs()
        self.generate_canvas()

    def generate_sprites(self):
        """Generate sprites to populate the image."""
        sprite_sizes = [5, 7, 10, 21, 36, 40]
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

    def generate_blobs(self, n_blobs: int = 1000):
        """Generate coordinates of blobs and their sizes.

        A 1000x3 array is returned. Each row represents (x,y) coordinate
        of the sprite and the index representing the size of the sprite.

        Blobs are characterised by X, Y, sprite
        We also generate a KD tree to rapidly find blobs in an image
        """
        self.blobs = np.zeros((n_blobs, 3))

        w = np.max(self.glyph_shape)
        self.blobs[:, 0] = RNG.uniform(w / 2, self.canvas_shape[0] - w / 2, n_blobs)
        self.blobs[:, 1] = RNG.uniform(w / 2, self.canvas_shape[1] - w / 2, n_blobs)
        self.blobs[:, 2] = RNG.choice(len(self.sprites), n_blobs)

    def generate_canvas(self):
        """Generate a canvas.

        Canvas is int16 so that random noise can be added to simulation image before
        changing to unit8 to stop wrapping.
        """
        self.blank_canvas = np.ones(self.canvas_shape, dtype=np.int16)
        self.blank_canvas[:, :, 0] *= BG_COLOR[0]
        self.blank_canvas[:, :, 1] *= BG_COLOR[1]
        self.blank_canvas[:, :, 2] *= BG_COLOR[2]
        self.canvas = self.blank_canvas.copy()
        w, h, _ = self.glyph_shape
        for x, y, sprite_size_index in self.blobs:
            self.canvas[
                int(x) - w // 2 : int(x) - w // 2 + w,
                int(y) - h // 2 : int(y) - h // 2 + h,
            ] -= self.sprites[int(sprite_size_index)]
        self.canvas[self.canvas < 0] = 0
        self.canvas[self.canvas > 255] = 255

    def generate_image(self, pos: tuple[int, int, int]):
        """Generate an image with blobs based on supplied coordinates."""
        canvas_width, canvas_height, _ = self.canvas_shape
        image_width, image_height, _ = self.shape
        pos = tuple(x * RATIO for x in pos)
        top_left = (
            int(pos[0]) - image_width // 2 - canvas_width // 2,
            int(pos[1]) - image_height // 2 - canvas_height // 2,
        )
        x_slice = slice(top_left[0], top_left[0] + self.shape[0])
        y_slice = slice(top_left[1], top_left[1] + self.shape[1])
        z_slice = slice(None)
        canvas = self.canvas if self._show_sample else self.blank_canvas
        focused_image = canvas[(x_slice, y_slice, z_slice)]
        image = gaussian_filter(
            focused_image,
            sigma=np.abs(pos[2]) / 5,
            axes=(0, 1),
        )
        if image.shape != self.shape:
            raise ValueError(
                f"Image shape {image.shape} does not match intended shape {self.shape}"
            )

        # Add noise and convert to uint8
        image += RNG.normal(scale=2, size=self.shape).astype("int16")
        image[image < 0] = 0
        image[image > 255] = 255
        return image.astype("uint8")

    def attach_to_server(
        self, server: lt.ThingServer, path: str, setting_storage_path: str
    ):
        """Wrap the attach_to_server method so the server instance can be stored.

        Direct access to the server instance is needed to get the stage position while
        maintaining the same public API as a real camera that doesn't need this access.
        """
        self._server = server
        return super().attach_to_server(server, path, setting_storage_path)

    def get_stage_position(self):
        """Return the stage position.

        The simulation camera has access to the stage position so it can generate a
        different image as the stage moves.
        """
        if not self._stage and self._server:
            self._stage = self._server.things["/stage/"]
        return self._stage.instantaneous_position

    def generate_frame(self):
        """Generate a frame with blobs based on the stage coordinates."""
        try:
            pos = self.get_stage_position()
        except Exception as e:
            print(f"Failed to get stage position: {e}")
            pos = {"x": 0, "y": 0, "z": 0}
        return self.generate_image((pos["y"], pos["x"], pos["z"]))

    def __enter__(self):
        """Start the capture thread when the Thing context manager is opened."""
        self._capture_enabled = True
        self._capture_thread = Thread(target=self._capture_frames)
        self._capture_thread.start()
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        """Close the capture thread when the Thing context manager is closed."""
        if self.stream_active:
            self._capture_enabled = False
            self._capture_thread.join()

    @lt.thing_property
    def stream_active(self) -> bool:
        """Whether the MJPEG stream is active."""
        if self._capture_enabled and self._capture_thread:
            return self._capture_thread.is_alive()
        return False

    def _capture_frames(self):
        portal = lt.get_blocking_portal(self)
        while self._capture_enabled:
            time.sleep(self.frame_interval)
            try:
                frame = self.generate_frame()
                jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
                self.mjpeg_stream.add_frame(jpeg, portal)
                jpeg_lores = cv2.imencode(".jpg", cv2.resize(frame, (320, 240)))[
                    1
                ].tobytes()
                self.lores_mjpeg_stream.add_frame(jpeg_lores, portal)
            except Exception as e:
                logging.error(f"Failed to capture frame: {e}, retrying...")

    @lt.thing_action
    def discard_frames(self) -> None:
        """Discard frames so that the next frame captured is fresh.

        There is nothing to do as this is a simulation!
        """

    @lt.thing_action
    def capture_array(
        self,
        resolution: Literal["main", "full"] = "full",
    ) -> ArrayModel:
        """Acquire one image from the camera and return as an array.

        This function will produce a nested list containing an uncompressed RGB image.
        It's likely to be highly inefficient - raw and/or uncompressed captures using
        binary image formats will be added in due course.
        """
        logging.warning(f"Simulation camera doesn't respect {resolution} setting")
        return self.generate_frame()

    @lt.thing_action
    def capture_jpeg(
        self,
        metadata_getter: lt.deps.GetThingStates,
        resolution: Literal["main", "full"] = "main",
    ) -> JPEGBlob:
        """Acquire one image from the camera and return as a JPEG blob.

        This function will produce a JPEG image.
        """
        logging.warning(f"Simulation camera doesn't respect {resolution} setting")
        frame = self.capture_array()
        jpeg = cv2.imencode(".jpg", frame)[1].tobytes()
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.UserComment: json.dumps(metadata_getter()).encode(
                    "utf-8"
                )
            },
            "GPS": {},
            "Interop": {},
            "1st": {},
            "thumbnail": None,
        }
        output = io.BytesIO()
        piexif.insert(piexif.dump(exif_dict), jpeg, output)
        return JPEGBlob.from_bytes(output.getvalue())

    @lt.thing_action
    def remove_sample(self):
        """Show the simulated background with no sample."""
        if not self._show_sample:
            raise RuntimeError("Sample is already removed.")
        self._show_sample = False

    @lt.thing_action
    def load_sample(self):
        """Show the simulated sample."""
        if self._show_sample:
            raise RuntimeError("Sample is already in place.")
        self._show_sample = True

    @lt.thing_property
    def secondary_calibration_actions(self) -> list[ActionButton]:
        """The calibration actions that appear only in settings panel."""
        return [
            action_button_for(self.load_sample, submit_label="Load Sample"),
            action_button_for(self.remove_sample, submit_label="Remove Sample"),
        ]
