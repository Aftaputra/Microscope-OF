# -*- coding: utf-8 -*-

"""
Raspberry Pi camera implementation of the PiCameraStreamer class.

**NOTES:**

Still port used for image capture.
Preview port reserved for onboard GPU preview.

Video port:

* Splitter port 0: Image capture (if `use_video_port == True`)
* Splitter port 1: Streaming frames
* Splitter port 2: Video capture
* Splitter port 3: [Currently unused]

PiCameraStreamer streams at video_resolution

Camera capture resolution set to stream_resolution in frames()

Video port uses that resolution for everything. If a different resolution
is specified for video capture, this is handled by the resizer.

Still capture (if use_video_port == False) uses pause_stream
to temporarily increase the capture resolution.
"""

import logging
import time

# Type hinting
from typing import Tuple

import numpy as np

# Pi camera
import picamerax
import picamerax.array

from openflexure_microscope.camera.base import BaseCamera
from openflexure_microscope.paths import settings_file_path
from openflexure_microscope.utilities import json_to_ndarray, ndarray_to_json

# Richard's fix gain
from .set_picamera_gain import set_analog_gain, set_digital_gain


# MAIN CLASS
class PiCameraStreamer(BaseCamera):
    """Raspberry Pi camera implementation of PiCameraStreamer."""

    picamera_settings_keys = [
        "exposure_mode",
        "analog_gain",
        "digital_gain",
        "shutter_speed",
        "awb_gains",
        "awb_mode",
        "framerate",
        "saturation",
        "iso",
        "brightness",
        "contrast",
        "crop",
        "drc_strength",
        "exposure_compensation",
        "image_effect",
        "meter_mode",
        "sharpness",
        "annotate_text",
        "annotate_text_size",
        "zoom",
    ]

    def __init__(self):
        # Run BaseCamera init
        BaseCamera.__init__(self)
        # Attach to Pi camera
        self.camera = (
            picamerax.PiCamera()
        )  #: :py:class:`picamerax.PiCamera`: Picamera object

        # Store state of PiCameraStreamer
        self.preview_active = False

        # Reset variable states
        self.set_zoom(1.0)

        # Set default settings
        self.image_resolution = tuple(
            self.camera.MAX_RESOLUTION
        )  #: tuple: Resolution for image captures
        self.stream_resolution = (
            832,
            624,
        )  #: tuple: Resolution for stream and video captures
        self.numpy_resolution = (
            1312,
            976,
        )  #: tuple: Resolution for numpy array captures
        self.jpeg_quality = 100  #: int: JPEG quality
        self.mjpeg_quality = 75  #: int: MJPEG quality

        # Start stream recording (and set resolution)
        self.start_stream_recording()
        # Wait until frames are available
        logging.debug("Waiting for frames...")
        self.stream.new_frame.wait()
        logging.debug("Camera initialised")

    @property
    def configuration(self):
        """The current camera configuration."""
        return {"board": self.camera.revision}

    @property
    def state(self):
        """The current read-only camera state."""
        return {}

    def close(self):
        """Close the Raspberry Pi PiCameraStreamer."""
        # Stop stream recording
        self.stop_stream_recording()
        # Run BaseCamera close method
        super().close()
        # Detach Pi camera
        if self.camera:
            self.camera.close()

    # HANDLE SETTINGS
    def read_settings(self) -> dict:
        """
        Return config dictionary of the PiCameraStreamer.
        """

        # Get config items from the base class
        conf_dict = BaseCamera.read_settings(self)

        # Include device-specific config items
        conf_dict.update(
            {
                "stream_resolution": self.stream_resolution,
                "image_resolution": self.image_resolution,
                "numpy_resolution": self.numpy_resolution,
                "jpeg_quality": self.jpeg_quality,
                "mjpeg_quality": self.mjpeg_quality,
                "picamera": {},
            }
        )

        # Include a subset of picamera properties. Excludes lens shading table
        for key in PiCameraStreamer.picamera_settings_keys:
            try:
                value = getattr(self.camera, key)
                logging.debug("Reading PiCamera().%s: %s", key, value)
                conf_dict["picamera"][key] = value
            except AttributeError:
                logging.debug("Unable to read PiCamera attribute %s", (key))

        # Include a serialised lens shading table
        if (
            hasattr(self.camera, "lens_shading_table")
            and getattr(self.camera, "lens_shading_table") is not None
        ):
            conf_dict["picamera"]["lens_shading_table"] = ndarray_to_json(
                getattr(self.camera, "lens_shading_table")
            )

        return conf_dict

    def update_settings(self, config: dict):
        """
        Write a config dictionary to the PiCameraStreamer config.

        The passed dictionary may contain other parameters not relevant to
        camera config. Eg. Passing a general config file will work fine.

        Args:
            config (dict): Dictionary of config parameters.
        """

        paused_stream = False
        logging.debug("PiCameraStreamer: Applying config:")
        logging.debug(config)

        with self.lock(timeout=None):

            # Apply valid config params to Picamera object
            if not self.record_active:  # If not recording a video

                # Pause stream while changing settings
                if self.stream_active:  # If stream is active
                    logging.info("Pausing stream to update config.")
                    self.stop_stream_recording()  # Pause stream
                    paused_stream = True  # Remember to unpause stream when done

                # PiCamera parameters
                if "picamera" in config:  # If new settings are given
                    self.apply_picamera_settings(
                        config["picamera"], pause_for_effect=True
                    )

                    # Handle lens shading if camera supports it
                    if (
                        hasattr(self.camera, "lens_shading_table")
                        and "lens_shading_table" in config["picamera"]
                    ):
                        try:
                            self.camera.lens_shading_table = json_to_ndarray(
                                config["picamera"].get("lens_shading_table")
                            )
                        except KeyError as e:
                            logging.error(e)

                # PiCameraStreamer parameters
                for key, value in config.items():  # For each provided setting
                    if (key != "picamera") and hasattr(self, key):
                        setattr(self, key, value)

                # If stream was paused to update config, unpause
                if paused_stream:
                    logging.info("Resuming stream.")
                    self.start_stream_recording()

            else:
                raise Exception(
                    "Cannot update camera config while recording is active."
                )

    def apply_picamera_settings(
        self, settings_dict: dict, pause_for_effect: bool = True
    ):
        """

        Args:
            settings_dict (dict): Dictionary of properties to apply to the :py:class:`picamerax.PiCamera`: object
            pause_for_effect (bool): Pause tactically to reduce risk of timing issues
        """
        # Set exposure mode
        if "exposure_mode" in settings_dict:
            logging.debug(
                "Applying exposure_mode: %s", (settings_dict["exposure_mode"])
            )
            self.camera.exposure_mode = settings_dict["exposure_mode"]

        # Apply gains and let them settle
        if "analog_gain" in settings_dict:
            logging.debug("Applying analog_gain: %s", (settings_dict["analog_gain"]))
            set_analog_gain(self.camera, float(settings_dict["analog_gain"]))
        if "digital_gain" in settings_dict:
            logging.debug("Applying digital_gain: %s", (settings_dict["digital_gain"]))
            set_digital_gain(self.camera, float(settings_dict["digital_gain"]))

        # Apply shutter speed
        if "shutter_speed" in settings_dict:
            logging.debug(
                "Applying shutter_speed: %s", (settings_dict["shutter_speed"])
            )
            self.camera.shutter_speed = int(settings_dict["shutter_speed"])

        time.sleep(0.2)  # Let gains settle

        # Handle AWB in a half-smart way
        if "awb_gains" in settings_dict:
            logging.debug("Applying awb_mode: off")
            self.camera.awb_mode = "off"
            logging.debug("Applying awb_gains: %s", (settings_dict["awb_gains"]))
            self.camera.awb_gains = settings_dict["awb_gains"]
        elif "awb_mode" in settings_dict:
            logging.debug("Applying awb_mode: %s", (settings_dict["awb_mode"]))
            self.camera.awb_mode = settings_dict["awb_mode"]

        # Handle some properties that can be quickly applied
        batched_keys = ["framerate", "saturation"]
        for key in batched_keys:
            if (key in settings_dict) and hasattr(self.camera, key):
                logging.debug("Applying %s: %s", key, settings_dict[key])
                setattr(self.camera, key, settings_dict[key])

        # Final optional pause to settle
        if pause_for_effect:
            time.sleep(0.2)

    def set_zoom(self, zoom_value: float = 1.0) -> None:
        """
        Change the camera zoom, handling re-centering and scaling.
        """
        with self.lock(timeout=None):
            self.zoom_value = float(zoom_value)
            if self.zoom_value < 1:
                self.zoom_value = 1
            # Richard's code for zooming !
            fov = self.camera.zoom
            centre = np.array([fov[0] + fov[2] / 2.0, fov[1] + fov[3] / 2.0])
            size = 1.0 / self.zoom_value
            # If the new zoom value would be invalid, move the centre to
            # keep it within the camera's sensor (this is only relevant
            # when zooming out, if the FoV is not centred on (0.5, 0.5)
            for i in range(2):
                if np.abs(centre[i] - 0.5) + size / 2 > 0.5:
                    centre[i] = 0.5 + (1.0 - size) / 2 * np.sign(centre[i] - 0.5)
            logging.info("setting zoom, centre %s, size %s", centre, size)
            new_fov = (centre[0] - size / 2, centre[1] - size / 2, size, size)
            self.camera.zoom = new_fov

    # LAUNCH ACTIONS

    def start_preview(self, fullscreen=True, window=None):
        """Start the on board GPU camera preview."""
        with self.lock(timeout=1):
            try:
                if not self.camera.preview:
                    logging.debug("Starting preview")
                    self.camera.start_preview(fullscreen=fullscreen, window=window)
                else:
                    logging.debug("Resizing preview")
                    if window:
                        self.camera.preview.window = window
                    if fullscreen:
                        self.camera.preview.fullscreen = fullscreen
                self.preview_active = True
            except picamerax.exc.PiCameraMMALError as e:
                logging.error(
                    "Suppressed a MMALError in start_preview. Exception: %s", (e)
                )
            except picamerax.exc.PiCameraValueError as e:
                logging.error(
                    "Suppressed a ValueError exception in start_preview. Exception: %s",
                    (e),
                )

    def stop_preview(self):
        """Stop the on board GPU camera preview."""
        with self.lock(timeout=1):
            if self.camera.preview:
                self.camera.stop_preview()
                self.preview_active = False

    def start_recording(self, output, fmt: str = "h264", quality: int = 15):
        """Start recording.

        Start a new video recording, writing to a output object.

        Args:
            output: String or file-like object to write capture data to
            fmt (str): Format of the capture.
            quality (int): Video recording quality.

        Returns:
            output_object (str/BytesIO): Target object.

        """
        with self.lock(timeout=5):
            # Start recording method only if a current recording is not running
            if not self.record_active:

                # Start the camera video recording on port 2
                logging.info("Recording to %s", (output))

                self.camera.start_recording(
                    output,
                    format=fmt,
                    splitter_port=2,
                    resize=self.stream_resolution,
                    quality=quality,
                )

                # Update state
                self.record_active = True

                return output

            else:
                logging.warning(
                    "Cannot start a new recording\
                    until the current recording has stopped."
                )
                return None

    def stop_recording(self):
        """Stop the last started video recording on splitter port 2."""
        with self.lock(timeout=5):
            # Stop the camera video recording on port 2
            logging.info("Stopping recording")
            self.camera.stop_recording(splitter_port=2)
            logging.info("Recording stopped")

            # Update state
            self.record_active = False

    def start_stream_recording(self, splitter_port: int = 1, **kwargs) -> None:
        """
        Sets the camera resolution to the video/stream resolution, and starts recording if the stream should be active.

        Args:
            splitter_port (int): Splitter port to start recording on
        """
        for k in kwargs.keys():
            logging.warning(
                "Warning, kwarg %s is invalid for stop_stream_recording.", k
            )
        with self.lock(timeout=None):
            # Reduce the resolution for video streaming
            try:
                self.camera._check_recording_stopped()  # pylint: disable=W0212
            except picamerax.exc.PiCameraRuntimeError:
                logging.info(
                    "Error while changing resolution: Recording already running."
                )
            else:
                self.camera.resolution = self.stream_resolution
                # Sprinkled a sleep to prevent camera getting confused by rapid commands
                time.sleep(0.2)

            # If the stream should be active
            try:
                # Start recording on stream port
                self.camera.start_recording(
                    self.stream,
                    format="mjpeg",
                    quality=self.mjpeg_quality,
                    bitrate=-1,  # RWB: disable bitrate control
                    # (bitrate control makes JPEG size less good as a focus
                    # metric)
                    splitter_port=splitter_port,
                )
            except picamerax.exc.PiCameraAlreadyRecording:
                logging.info("Error while starting preview: Recording already running.")
            else:
                self.stream_active = True
                logging.debug(
                    "Started MJPEG stream at %s on port %s",
                    self.stream_resolution,
                    splitter_port,
                )

    def stop_stream_recording(self, splitter_port: int = 1, **kwargs) -> None:
        """
        Sets the camera resolution to the still-image resolution, and stops recording if the stream is active.

        Args:
            splitter_port (int): Splitter port to stop recording on
        """
        for k in kwargs.keys():
            logging.warning(
                "Warning, kwarg %s is invalid for stop_stream_recording.", k
            )
        with self.lock:
            # Stop the camera video recording on port 1
            try:
                self.camera.stop_recording(splitter_port=splitter_port)
            except picamerax.exc.PiCameraNotRecording:
                logging.info("Not recording on splitter_port %s", (splitter_port))
            else:
                self.stream_active = False
                logging.info(
                    "Stopped MJPEG stream on port %s. Switching to %s.",
                    splitter_port,
                    self.image_resolution,
                )

            # Increase the resolution for taking an image
            time.sleep(
                0.2
            )  # Sprinkled a sleep to prevent camera getting confused by rapid commands
            self.camera.resolution = self.image_resolution

    def capture(
        self,
        output,
        fmt: str = "jpeg",
        use_video_port: bool = False,
        resize: Tuple[int, int] = None,
        bayer: bool = True,
        thumbnail: tuple = None,
    ):
        """
        Capture a still image to a StreamObject.

        Defaults to JPEG format.
        Target object can be overridden for development purposes.

        Args:
            output: String or file-like object to write capture data to
            fmt (str): Format of the capture.
            use_video_port (bool): Capture from the video port used for streaming. Lower resolution, faster.
            resize ((int, int)): Resize the captured image.
            bayer (bool): Store raw bayer data in capture

        Returns:
            output_object (str/BytesIO): Target object.
        """
        with self.lock:
            logging.info("Capturing to %s", (output))

            # Set resolution and stop stream recording if necessary
            if not use_video_port:
                self.stop_stream_recording()

            self.camera.capture(
                output,
                format=fmt,
                quality=self.jpeg_quality,
                resize=resize,
                bayer=(not use_video_port) and bayer,
                use_video_port=use_video_port,
                thumbnail=thumbnail,
            )

            # Set resolution and start stream recording if necessary
            if not use_video_port:
                self.start_stream_recording()

            return output

    def array(self, use_video_port=True) -> np.ndarray:
        """Capture an uncompressed still RGB image to a Numpy array.

        Args:
            use_video_port (bool): Capture from the video port used for streaming. Lower resolution, faster.
            resize ((int, int)): Resize the captured image.

        Returns:
            output_array (np.ndarray): Output array of capture
        """
        with self.lock:
            logging.debug("Creating PiRGBArray")
            with picamerax.array.PiRGBArray(self.camera) as output:
                logging.info("Capturing to %s", (output))
                self.camera.capture(output, format="rgb", use_video_port=use_video_port)
                return output.array
