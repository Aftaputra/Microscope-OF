# -*- coding: utf-8 -*-

"""
Raspberry Pi camera implementation of the StreamingCamera class.

NOTES:
Still port used for image capture
Preview port reserved for onboard GPU preview
Video port:
    Splitter port 0: Image capture (if use_video_port == True)
    Splitter port 1: Streaming frames
    Splitter port 2: Video capture
    Splitter port 3: [Currently unused]

StreamingCamera streams at video_resolution
Camera capture resolution set to video_resolution in frames()
Video port uses that resolution for everything. If a different resolution
is specified for video capture, this is handled by the resizer.

Still capture (if use_video_port == False) uses pause_stream
to temporarily increase the capture resolution.
"""

from __future__ import division

import io
import time
import datetime
import sys
import os
import yaml
import copy
import numpy as np
from PIL import Image
import logging

# Used for conversion only
from fractions import Fraction

# Pi camera
import picamera
import picamera.array

# Type hinting
from typing import Tuple

# Threading
import threading

from .base import BaseCamera, CaptureObject
# Richard's fix gain
from .set_picamera_gain import set_analog_gain, set_digital_gain

PICAMERA_KEYS = [
    'exposure_mode',
    'awb_mode',
    'awb_gains',
    'framerate',
    'shutter_speed',
    'saturation', ]

CONFIG_KEYS = [
    'video_resolution',
    'image_resolution',
    'numpy_resolution',
    'jpeg_quality',
    'analog_gain',
    'digital_gain',
    'shading_table_path']


def fractions_to_floats(value):
    """Deal with horrible, horrible PiCamera fractions"""
    result = value
    if type(value) is list or type(value) is tuple:
        result = [float(v) if isinstance(v, Fraction) else v for v in value]
        if type(value) is tuple:
            result = tuple(result)
    else:
        if isinstance(value, Fraction):
            result = float(value)
    return result


class StreamingCamera(BaseCamera):
    """Raspberry Pi camera implementation of StreamingCamera.

    Args:
        config (dict): Dictionary of config parameters to apply on init. If None, will default to basic config.
    """
    def __init__(self, config: dict=None):
        # Run BaseCamera init
        BaseCamera.__init__(self)
        # Attach to Pi camera
        self.camera = picamera.PiCamera()  #: :py:class:`picamera.PiCamera`: Picamera object

        # Store state of StreamingCamera
        self.state.update({
            'stream_active': False,
            'record_active': False,
            'preview_active': False,
        })
        # Reset variable states
        self.set_zoom(1.0)

        # Default camera config
        self._config.update({
            'video_resolution': (832, 624),
            'image_resolution': (2592, 1944),
            'numpy_resolution': (1312, 976),
            'jpeg_quality': 75,
        })

        # Load config dictionary if passed
        if config:
            self.config = config

        # Start streaming
        self.start_worker()

    def initialisation(self):
        """Run any initialisation code when the frame iterator starts."""
        pass

    def close(self):
        """Close the Raspberry Pi StreamingCamera."""
        # Run BaseCamera close method
        BaseCamera.close(self)
        # Detatch Pi camera
        if self.camera:
            self.camera.close()

    # HANDLE SETTINGS
    @property
    def supports_lens_shading(self):
        """Determine whether the picamera module supports lens shading.

        As of March 2018, picamera did not wrap the necessary MMAL commands to
        set the lens shading table, or to write the value of analog or digital
        gain.  I have a forked version of the library that does support these.
        For ease of use by people who don't want those features, this library
        does not have a hard dependency on lens shading.  However, we need to
        check in some places whether it's available.
        """
        return hasattr(self.camera, "lens_shading_table")

    def apply_shading_table(self):
        if not self.supports_lens_shading:
            logging.error("the currently-installed picamera library does not support all "
            "the features of the openflexure microscope software.  These features "
            "include lens shading control and setting the analog/digital gain.\n"
            "\n"
            "See the installation instructions for how to fix this:\n"
            "https://github.com/rwb27/openflexure_microscope_software")
        elif 'shading_table_path' not in self.config:
            logging.warning("No shading table path given in config.")
        else:
            logging.debug("Applying shading table from {}".format(self.config['shading_table_path']))
            npy = np.load(self.config['shading_table_path'])
            self.camera.lens_shading_table = npy

    @property
    def config(self):
        """
        Return config dictionary of the StreamingCamera.
        """
        global PICAMERA_KEYS, CONFIG_KEYS

        conf_dict = {
            'picamera_params': {},
        }

        # PiCamera parameters (obtained directly from PiCamera object)
        for key in PICAMERA_KEYS:
            try:
                value = getattr(self.camera, key)
                value = fractions_to_floats(value)
                conf_dict['picamera_params'][key] = value
            except AttributeError:
                logging.warning("Unable to read PiCamera attribute {}".format(key))

        # StreamingCamera parameters (obtained from StreamingCamera _config)
        for key in CONFIG_KEYS:
            if key in self._config:
                conf_dict[key] = self._config[key]

        return conf_dict

    @config.setter
    def config(self, config: dict) -> None:
        """
        Write a config dictionary to the StreamingCamera config.

        The passed dictionary may contain other parameters not relevant to
        camera config. Eg. Passing a general config file will work fine.

        Args:
            config (dict): Dictionary of config parameters.
        """
        global PICAMERA_KEYS, CONFIG_KEYS

        paused_stream = False

        # Apply valid config params to Picamera object
        if not self.state['record_active']:  # If not recording a video

            logging.debug("Applying config:")
            logging.debug(config)

            # Pause stream while changing settings
            if self.state['stream_active']:  # If stream is active
                logging.info("Pausing stream to update config.")
                self.stop_stream_recording()  # Pause stream
                paused_stream = True  # Remember to unpause stream when done

            # PiCamera parameters (applied directly to PiCamera object)
            if 'picamera_params' in config:
                for key in PICAMERA_KEYS:
                    if key in config['picamera_params']:
                        logging.debug("Setting parameter {}: {}".format(key, config['picamera_params'][key]))
                        setattr(self.camera, key, config['picamera_params'][key])

            # StreamingCamera parameters (applied via StreamingCamera config)
            for key in CONFIG_KEYS:
                if key in config:
                    logging.debug("Setting parameter {}: {}".format(key, config[key]))
                    self._config[key] = config[key]

            # Richard's library to set analog and digital gains
            if 'analog_gain' in config:
                set_analog_gain(self.camera, config['analog_gain'])
            if 'digital_gain' in config:
                set_digital_gain(self.camera, config['digital_gain'])

            # Handle lens shading, if a new one is given
            if 'shading_table_path' in config:
                self.apply_shading_table()

            # If stream was paused to update config, unpause
            if paused_stream:
                logging.info("Resuming stream.")
                self.start_stream_recording()

        else:
            raise Exception(
                "Cannot update camera config while recording is active.")

    def set_zoom(self, zoom_value: float=1.) -> None:
        """
        Change the camera zoom, handling recentering and scaling.
        """
        self.state['zoom_value'] = float(zoom_value)
        if self.state['zoom_value'] < 1:
            self.state['zoom_value'] = 1
        # Richard's code for zooming !
        fov = self.camera.zoom
        centre = np.array([fov[0] + fov[2]/2.0, fov[1] + fov[3]/2.0])
        size = 1.0/self.state['zoom_value']
        # If the new zoom value would be invalid, move the centre to
        # keep it within the camera's sensor (this is only relevant
        # when zooming out, if the FoV is not centred on (0.5, 0.5)
        for i in range(2):
            if np.abs(centre[i] - 0.5) + size/2 > 0.5:
                centre[i] = 0.5 + (1.0 - size)/2 * np.sign(centre[i]-0.5)
        logging.info("setting zoom, centre {}, size {}".format(centre, size))
        new_fov = (centre[0] - size/2, centre[1] - size/2, size, size)
        self.camera.zoom = new_fov

    # LAUNCH ACTIONS

    def start_preview(self) -> bool:
        """Start the onboard GPU camera preview."""
        self.camera.start_preview()
        self.state['preview_active'] = True
        return True

    def stop_preview(self) -> bool:
        """Stop the onboard GPU camera preview."""
        self.camera.stop_preview()
        self.state['preview_active'] = False
        return True

    def start_recording(
            self,
            output,
            fmt: str='h264',
            quality: int=15):
        """Start recording.

        Start a new video recording, writing to a output object.

        Args:
            output (CaptureObject/str): Output object to write data bytes to.
            write_to_file (bool/NoneType): Should the StreamObject write to a file?
            filename (str): Name of the stored file.  Defaults to timestamp.
            fmt (str): Format of the capture.

        Returns:
            output_object (str/BytesIO): Target object.

        """
        # Start recording method only if a current recording is not running
        if not self.state['record_active']:

            # If output is a StreamObject
            if isinstance(output, CaptureObject):
                # Lock the StreamObject while recording
                output.lock()
                # Set target to capture stream
                output_stream = output.stream
            else:
                output_stream = output

            # Start the camera video recording on port 2
            logging.info("Recording to {}".format(output))

            self.camera.start_recording(
                output_stream,
                format=fmt,
                splitter_port=2,
                resize=self.config['video_resolution'],
                quality=quality)

            # Update state dictionary
            self.state['record_active'] = True

            return output

        else:
            logging.error(
                "Cannot start a new recording\
                until the current recording has stopped.")
            return None

    def stop_recording(self) -> bool:
        """Stop the last started video recording on splitter port 2."""
        # Stop the camera video recording on port 2
        logging.info("Stopping recording")
        self.camera.stop_recording(splitter_port=2)
        logging.info("Recording stopped")

        # Update state dictionary
        self.state['record_active'] = False

    def stop_stream_recording(
            self,
            splitter_port: int=1,
            resolution: Tuple[int, int]=None) -> None:
        """
        Sets the camera resolution to the still-image resolution, and stops recording if the stream is active.

        Args:
            splitter_port (int): Splitter port to stop recording on
            resolution ((int, int)): Resolution to set the camera to, after stopping recording.
        """
        # If no resolution is specified, default to image_resolution
        if not resolution:
            resolution = self.config['image_resolution']

        # Stop the camera video recording on port 1
        try:
            self.camera.stop_recording(splitter_port=splitter_port)
            logging.info("Stopped MJPEG stream on port {1}. Switching to {0}.".format(resolution, splitter_port))
        except picamera.exc.PiCameraNotRecording:
            logging.info("Not recording on splitter_port {}".format(splitter_port))

        # Increase the resolution for taking an image
        self.camera.resolution = resolution

    def start_stream_recording(
            self,
            splitter_port: int=1,
            resolution: Tuple[int, int]=None) -> None:
        """
        Sets the camera resolution to the video/stream resolution, and starts recording if the stream should be active.

        Args:
            splitter_port (int): Splitter port to start recording on
            resolution ((int, int)): Resolution to set the camera to, before starting recording. Defaults to `self.config['video_resolution']`.
        """

        # If no stream object exists
        if not hasattr(self, 'stream'):
            self.stream = io.BytesIO() # Create a stream object

        # If no explicit resolution is passed
        if not resolution:
            resolution = self.config['video_resolution']  # Default to video recording resolution

        # Reduce the resolution for video streaming
        self.camera.resolution = resolution

        # If the stream should be active
        if self.state['stream_active']:
            # Start recording on stream port
            self.camera.start_recording(
                self.stream,
                format='mjpeg',
                quality=self.config['jpeg_quality'],
                splitter_port=splitter_port)
            
            logging.debug("Started MJPEG stream at {} on port {}".format(resolution, splitter_port))

    def capture(
            self,
            output,
            fmt: str='jpeg',
            use_video_port: bool=False,
            resize: Tuple[int, int]=None,
            bayer: bool=True):
        """
        Capture a still image to a StreamObject.

        Defaults to JPEG format.
        Target object can be overridden for development purposes.

        Args:
            output (CaptureObject/str): Output object to write data bytes to.
            use_video_port (bool): Capture from the video port used for streaming. Lower resolution, faster.
            fmt (str): Format of the capture.
            resize ((int, int)): Resize the captured image.
        """

        # If output is a StreamObject
        if isinstance(output, CaptureObject):
            # Set target to capture stream
            output_stream = output.stream
        else:
            output_stream = output

        logging.info("Capturing to {}".format(output))

        # Set resolution and stop stream recording if necesarry
        if not use_video_port:
            self.stop_stream_recording()

        self.camera.capture(
            output_stream,
            format=fmt,
            quality=100,
            resize=resize,
            bayer=(not use_video_port) and bayer,
            use_video_port=use_video_port)

        # Set resolution and start stream recording if necesarry
        if not use_video_port:
            self.start_stream_recording()

        return output

    def yuv(
            self,
            rgb=False,
            use_video_port: bool=True,
            resize: Tuple[int, int]=None) -> np.ndarray:
        """Capture an uncompressed still YUV image to a Numpy array.

        Args:
            use_video_port (bool): Capture from the video port used for streaming. Lower resolution, faster.
            resize ((int, int)): Resize the captured image.
        """
        if use_video_port:
            resolution = self.config['video_resolution']
        else:
            resolution = self.config['numpy_resolution']

        if resize:
            size = resize
        else:
            size = resolution

        if not use_video_port:
            self.stop_stream_recording(resolution=resolution)

        logging.debug("Creating PiYUVArray")
        with picamera.array.PiYUVArray(self.camera, size=size) as output:

            logging.info("Capturing to {}".format(output))

            self.camera.capture(
                output,
                resize=size,
                format='yuv',
                use_video_port=use_video_port)

            if not use_video_port:
                self.start_stream_recording()

            if rgb:
                logging.debug("Converting to RGB")
                return output.rgb_array
            else:
                return output.array

    def array(
            self,
            use_video_port: bool=True,
            resize: Tuple[int, int]=None) -> np.ndarray:
        """Capture an uncompressed still RGB image to a Numpy array.

        Args:
            use_video_port (bool): Capture from the video port used for streaming. Lower resolution, faster.
            resize ((int, int)): Resize the captured image.
        """

        if use_video_port:
            resolution = self.config['video_resolution']
        else:
            resolution = self.config['numpy_resolution']

        if resize:
            size = resize
        else:
            size = resolution

        # Always pause stream, to prevent resizer memory issues
        self.stop_stream_recording(resolution=resolution)

        logging.debug("Creating PiRGBArray")
        with picamera.array.PiRGBArray(self.camera, size=size) as output:

            logging.info("Capturing to {}".format(output))

            self.camera.capture(
                output,
                resize=size,
                format='rgb',
                use_video_port=use_video_port)

            # Resume stream
            self.start_stream_recording()

            return output.array

    # HANDLE STREAM FRAMES

    def frames(self):
        """
        Create generator that returns frames from the camera.

        Records video from port 1 to a byte stream,
        and iterates sequential frames.
        """
        # Run this initialisation method
        self.initialisation()
        self.wait_for_camera()

        # Start stream recording (and set resolution)
        self.start_stream_recording()

        # Update state
        logging.debug("STREAM ACTIVE")
        #self.state['stream_active'] = True

        # While the iterator is not closed
        try:
            while True:
                # reset stream for next frame
                self.stream.seek(0)
                self.stream.truncate()
                # to stream, read the new frame
                time.sleep(1/self.camera.framerate*0.1)
                # yield the result to be read
                frame = self.stream.getvalue()

                # ensure the size of package is right
                if len(frame) == 0:
                    pass
                else:
                    yield frame
        # When GeneratorExit or StopIteration raised, run cleanup code
        finally:
            # Stop stream recording (and set resolution)
            self.stop_stream_recording()

            logging.debug("FRAME ITERATOR END")
