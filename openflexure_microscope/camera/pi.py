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

Still capture (if use_video_port == False) uses pause_stream_for_capture
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

# Pi camera
import picamera
import picamera.array

# Type hinting
from typing import Tuple

# Threading
import threading

from .base import BaseCamera, StreamObject
# Richard's fix gain
from .set_picamera_gain import set_analog_gain, set_digital_gain
# Manage config
from .config import load_config

HERE = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG = os.path.join(HERE, 'config_picamera.yaml')


class StreamingCamera(BaseCamera):
    def __init__(self):
        """Raspberry Pi camera implementation of StreamingCamera."""
        # Run BaseCamera init
        BaseCamera.__init__(self)
        # Attach to Pi camera
        self.camera = picamera.PiCamera()

        # Camera settings
        self.settings.update({
            'video_resolution': (832, 624),
            'image_resolution': (2592, 1944),
            'numpy_resolution': (1312, 976),
            'jpeg_quality': 75,
        })

        # Store state of StreamingCamera
        self.state.update({
            'stream_active': False,
            'record_active': False,
            'preview_active': False,
        })

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

    # TODO: Handle exceptions
    # TODO: Have this take a dictionary (not a config file)
    # TODO: Web API entry point to send settings as JSON to this method
    # TODO: Separate method to store current settings back to YAML file
    # TODO: API entry point to get settings to JSON
    def update_settings(self, config_path: str=None) -> None:
        """Open config_picamera.yaml file and write to camera."""
        global DEFAULT_CONFIG

        paused_stream = False

        if not self.state['record_active']:  # If not recording a video

            if self.state['stream_active']:  # If stream is active
                logging.info("Pausing stream to update settings.")
                self.pause_stream_for_capture()  # Pause stream
                paused_stream = True  # Remember to unpause stream when done

            if not config_path:
                config = load_config(DEFAULT_CONFIG)
            else:
                config = load_config(config_path)

            logging.debug(config)

            # StreamingCamera settings
            if 'video_resolution' in config:
                self.settings['video_resolution'] = config['video_resolution']
            if 'image_resolution' in config:
                self.settings['image_resolution'] = config['image_resolution']
            if 'numpy_resolution' in config:
                self.settings['numpy_resolution'] = config['numpy_resolution']

            if 'jpeg_quality' in config:
                self.settings['jpeg_quality'] = config['jpeg_quality']
            if 'framerate' in config:
                self.settings['framerate'] = config['framerate']

            # Camera AWB
            if 'awb_mode' in config:
                self.camera.awb_mode = config['awb_mode']
            if 'red_gain' in config and 'blue_gain' in config:
                self.camera.awb_gains = (
                    config['red_gain'],
                    config['blue_gain'])

            # Camera framerate
            if 'framerate' in config:
                self.camera.framerate = config['framerate']
            # Camera exposure
            if 'shutter_speed' in config:
                self.camera.shutter_speed = config['shutter_speed']
            if 'saturation' in config:
                self.camera.saturation = config['saturation']
            # Camera misc.
            self.camera.led = False
            # Richard's library to set analog and digital gains
            if 'analog_gain' in config:
                set_analog_gain(self.camera, config['analog_gain'])
            if 'digital_gain' in config:
                set_digital_gain(self.camera, config['digital_gain'])

            if paused_stream:  # If stream was paused to update settings
                logging.info("Resuming stream.")
                self.resume_stream_for_capture()

        else:
            raise Exception(
                "Cannot update camera settings while recording is active.")

    def change_zoom(self, zoom_value: int=1) -> None:
        """Change the camera zoom, handling recentering and scaling."""
        zoom_value = float(zoom_value)
        if zoom_value < 1:
            zoom_value = 1
        # Richard's code for zooming !
        fov = self.camera.zoom
        centre = np.array([fov[0] + fov[2]/2.0, fov[1] + fov[3]/2.0])
        size = 1.0/zoom_value
        # If the new zoom value would be invalid, move the centre to
        # keep it within the camera's sensor (this is only relevant
        # when zooming out, if the FoV is not centred on (0.5, 0.5)
        for i in range(2):
            if np.abs(centre[i] - 0.5) + size/2 > 0.5:
                centre[i] = 0.5 + (1.0 - size)/2 * np.sign(centre[i]-0.5)
        print("setting zoom, centre {}, size {}".format(centre, size))
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
            target=None,
            write_to_file: bool=True,
            filename: str=None,
            folder: str='record',
            fmt: str='h264',
            quality: int=15):
        """Start a new video recording, writing to a target object.

        target (str/BytesIO): Target object to write bytes to.
            (default StreamObject)
        write_to_file (bool/NoneType): Should the StreamObject write to a file?
            (default True for video capture)
        filename (str): Name of the stored file.
            (defaults to timestamp)
        folder (str): Relative directory to store data file in.
        fmt (str): Format of the capture.
            (default 'h264')
        """
        # Start recording method only if a current recording is not running
        if not self.state['record_active']:

            # If no target is specified, store to StreamingCamera
            if not target:
                # Create a new video and add to the video list
                target_obj = self.new_video(StreamObject(
                    write_to_file=write_to_file,
                    filename=filename,
                    folder=folder,
                    fmt=fmt))

                # Lock the StreamObject while recording
                target_obj.lock()
                # Store to the StreamObject target
                target = target_obj.target

            else:
                target_obj = target

            # Start the camera video recording on port 2
            logging.info("Recording to {}".format(target))

            self.camera.start_recording(
                target,
                format=fmt,
                splitter_port=2,
                resize=self.settings['video_resolution'],
                quality=quality)

            # Update state dictionary
            self.state['record_active'] = True

            return target_obj

        else:
            print(
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

    def pause_stream_for_capture(
            self,
            splitter_port: int=1,
            resolution: Tuple[int, int]=None) -> None:
        """
        Pause capture on a splitter port.

        splitter_port (int): Splitter port to stop recording on
        resolution ((int, int)): Resolution to set the camera to,
            after stopping recording.
        """
        logging.debug("Pausing stream")
        # If no resolution is specified, default to image_resolution
        if not resolution:
            resolution = self.settings['image_resolution']

        # Stop the camera video recording on port 1
        self.camera.stop_recording(splitter_port=splitter_port)

        # Increase the resolution for taking an image
        self.camera.resolution = resolution

    def resume_stream_for_capture(
            self,
            splitter_port: int=1,
            resolution: Tuple[int, int]=None) -> None:
        """
        Resume capture on a splitter port.

        splitter_port (int): Splitter port to start recording on
        resolution ((int, int)): Resolution to set the camera to,
            before starting recording.
        """
        logging.debug("Unpausing stream")
        if not resolution:
            resolution = self.settings['video_resolution']

        # Reduce the resolution for video streaming
        self.camera.resolution = resolution

        # Resume the video channel
        self.camera.start_recording(
            self.stream,
            format='mjpeg',
            quality=self.settings['jpeg_quality'],
            splitter_port=splitter_port)

    def capture(
            self,
            target=None,
            write_to_file: bool=False,
            use_video_port: bool=False,
            filename: str=None,
            folder: str='capture',
            fmt: str='jpeg',
            resize: Tuple[int, int]=None):
        """
        Capture a still image to a StreamObject.

        Defaults to JPEG format.
        Target object can be overridden for development purposes.

        target (str/BytesIO): Target object to write data bytes to.
        write_to_file (bool): Should the StreamObject write to a file,
            instead of BytesIO stream?
        use_video_port (bool): Capture from the video port used for streaming.
            (lower resolution, faster)
        filename (str): Name of the stored file.
            (defaults to timestamp)
        folder (str): Relative directory to store data file in.
        fmt (str): Format of the capture.
            (default 'h264')
        resize ((int, int)): Resize the captured image.
        """
        # If no target is specified, store to StreamingCamera
        if not target:
            # Create a new image and add to the image list
            target_obj = self.new_image(StreamObject(
                write_to_file=write_to_file,
                filename=filename,
                folder=folder,
                fmt=fmt))
            target = target_obj.target  # Store to the StreamObject BytesIO

        else:
            target_obj = target

        logging.info("Capturing to {}".format(target))

        if not use_video_port:

            # Pause video splitter port 1
            self.pause_stream_for_capture()

            self.camera.capture(
                target,
                format=fmt,
                quality=100,
                resize=resize,
                bayer=True)

            # Resume video splitter port 1
            self.resume_stream_for_capture()

        else:
            self.camera.capture(
                target,
                format=fmt,
                quality=100,
                resize=resize,
                bayer=False,
                use_video_port=True)

        # Update state dictionary
        self.state['image_recent'] = str(target_obj)

        return target_obj

    def array(
            self,
            rgb=False,
            use_video_port: bool=True,
            resize: Tuple[int, int]=None) -> np.ndarray:
        """Capture an uncompressed still YUV image to a Numpy array.

        use_video_port (bool): Capture from the video port used for streaming.
            (lower resolution, faster)
        resize ((int, int)): Resize the captured image.
        """
        if use_video_port:
            resolution = self.settings['video_resolution']
        else:
            resolution = self.settings['numpy_resolution']

        if resize:
            size = resize
        else:
            size = resolution

        if not use_video_port:
            self.pause_stream_for_capture(resolution=resolution)

        logging.debug("Creating PiYUVArray")
        with picamera.array.PiYUVArray(self.camera, size=size) as output:

            logging.info("Capturing to {}".format(output))

            self.camera.capture(
                output,
                resize=size,
                format='yuv',
                use_video_port=use_video_port)

            if not use_video_port:
                self.resume_stream_for_capture()

            if rgb:
                logging.debug("Converting to RGB")
                return output.rgb_array
            else:
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

        # Settings config
        self.update_settings()
        # Set stream resolution
        self.camera.resolution = self.settings['video_resolution']

        # Create stream
        self.stream = io.BytesIO()

        # Start recording on video splitter port 1
        self.camera.start_recording(
            self.stream,
            format='mjpeg',
            quality=self.settings['jpeg_quality'],
            splitter_port=1)

        # Update state
        logging.debug("STREAM ACTIVE")
        self.state['stream_active'] = True

        # While the iterator is not closed
        try:
            while True:
                # reset stream for next frame
                self.stream.seek(0)
                self.stream.truncate()
                # to stream, read the new frame
                time.sleep(1/self.settings['framerate']*0.1)
                # yield the result to be read
                frame = self.stream.getvalue()

                # ensure the size of package is right
                if len(frame) == 0:
                    pass
                else:
                    yield frame
        # When GeneratorExit or StopIteration raised, run cleanup code
        finally:
            logging.debug("Stopping stream recording on port 1")
            self.camera.stop_recording(splitter_port=1)
            self.state['stream_active'] = False
            logging.debug("FRAME ITERATOR END")
