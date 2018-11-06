#!/usr/bin/env python
from openflexure_microscope.camera.pi import StreamingCamera, StreamObject, log
import os
import io
import sys
import time
import numpy as np
import uuid

from PIL import Image

import unittest

success_string = """
            /O
           | |
      _____) \\
     (__0)    \\______
    (____0)
    (____0)        EVERYTHING IS OK!
     (__o)___________
    """


def wait_for_cam(camera, timeout=5):
    """Wait for camera object in global namespace, with 5 second timeout."""
    timeout_time = time.time() + timeout
    while not camera:
        if time.time() > timeout_time:
            raise TimeoutError("Timeout waiting for camera")
        else:
            pass


class TestCaptureMethods(unittest.TestCase):

    def test_still_capture(self):
        """Tests capturing still images to a BytesIO stream."""
        global camera

        for use_video_port in [True, False]:
            for resize in [None, (640, 480)]:
                # Create unique ID
                id = uuid.uuid4().hex

                log("Resize: {}, V_Port: {}, ID: {}".format(
                    resize,
                    use_video_port,
                    id))

                # Wait for camera
                wait_for_cam(camera)

                # Capture to a context (auto-deletes files when done)
                with camera.capture(
                        write_to_file=False,
                        use_video_port=use_video_port,
                        filename=id,
                        resize=resize) as stream:

                    # Ensure file deletion fails and returns False
                    self.assertFalse(stream.delete())
                    # Ensure capture not stored to file
                    self.assertFalse(os.path.isfile(stream.file))

                    # BEFORE DELETE: Ensure StreamObject 'stream' has
                    # a valid BytesIO object and byte string
                    self.assertTrue(isinstance(
                        stream.data,
                        io.IOBase
                        ))
                    self.assertTrue(isinstance(
                        stream.binary,
                        (bytes, bytearray)
                        ))

                    # Save capture to file
                    stream.save()
                    # Check file got saved
                    self.assertTrue(os.path.isfile(stream.file))

                    # Delete file
                    stream.delete()
                    # Check file got deleted
                    self.assertFalse(os.path.isfile(stream.file))

                    # AFTER DELETE: Ensure StreamObject 'stream' has
                    # a valid BytesIO object and byte string
                    self.assertTrue(isinstance(stream.data, io.IOBase))
                    self.assertTrue(isinstance(
                        stream.binary,
                        (bytes, bytearray)
                        ))

                    # Create a PIL image from stream
                    image = Image.open(stream.data)

                    # Ensure a valid PIL image was created
                    self.assertTrue(isinstance(image, Image.Image))

                    # Calculate expected dimensions
                    if resize:
                        dims = resize
                    else:
                        if use_video_port:
                            dims = camera.settings['video_resolution']
                        else:
                            dims = camera.settings['image_resolution']

                    # Ensure PIL image size matches expected size
                    print(image.size, dims)
                    self.assertTrue(image.size == dims)

    def test_still_store(self):
        """Tests capturing still images to a file on disk."""
        global camera

        for use_video_port in [True, False]:
            for resize in [None, (640, 480)]:
                # Create unique ID
                id = uuid.uuid4().hex

                # Wait for camera
                wait_for_cam(camera)

                # Capture
                stream = camera.capture(
                    write_to_file=True,
                    use_video_port=use_video_port,
                    filename=id,
                    resize=resize)

                # Check file got saved
                self.assertTrue(os.path.isfile(stream.file))
                statinfo = os.stat(stream.file)
                self.assertTrue(statinfo.st_size > 0)

                # Ensure StreamObject 'stream' has
                # a valid BytesIO object and byte string
                self.assertTrue(isinstance(stream.data, io.IOBase))
                self.assertTrue(isinstance(stream.binary, (bytes, bytearray)))

                # Ensure file deletion completes and returns True
                self.assertTrue(stream.delete())

                # Check file got deleted
                self.assertFalse(os.path.isfile(stream.file))


class TestUnencodedMethods(unittest.TestCase):

    def test_yuv_array(self):
        """Tests capturing unencoded YUV data to a Numpy array."""
        global camera

        for use_video_port in [True, False]:
            for resize in [None, (640, 480)]:
                # Create unique ID
                id = uuid.uuid4().hex

                print("{}, {}, {}".format(id, resize, use_video_port))

                # Wait for camera
                wait_for_cam(camera)

                # Capture RGB array
                yuv = camera.array(
                    use_video_port=use_video_port,
                    resize=resize)

                # Ensure capture output is a valid numpy array
                self.assertTrue(isinstance(yuv, np.ndarray))

                # Calculate expected dimensions
                if resize:
                    dims = resize
                else:
                    if use_video_port:
                        dims = camera.settings['video_resolution']
                    else:
                        dims = camera.settings['numpy_resolution']

                # Ensure array shape matches expected dimensions
                self.assertTrue(yuv.shape == (dims[1], dims[0], 3))

    def test_rgb_array(self):
        """Tests capturing unencoded YUV/RGB data to a Numpy array."""
        global camera

        for use_video_port in [True, False]:
            for resize in [None, (640, 480)]:
                # Create unique ID
                id = uuid.uuid4().hex

                print("{}, {}, {}".format(id, resize, use_video_port))

                # Wait for camera
                wait_for_cam(camera)

                # Capture RGB array
                rgb = camera.array(
                    rgb=True,
                    use_video_port=use_video_port,
                    resize=resize)

                # Ensure capture output is a valid numpy array
                self.assertTrue(isinstance(rgb, np.ndarray))

                # Calculate expected dimensions
                if resize:
                    dims = resize
                else:
                    if use_video_port:
                        dims = camera.settings['video_resolution']
                    else:
                        dims = camera.settings['numpy_resolution']

                # Ensure array shape matches expected dimensions
                self.assertTrue(rgb.shape == (dims[1], dims[0], 3))


class TestRecordMethods(unittest.TestCase):

    def test_video_record(self):
        """Tests recording videos to BytesIO stream, and to file on disk."""
        global camera

        for write_to_file in [True, False, None]:

            # Create unique ID
            id = uuid.uuid4().hex

            # Wait for camera
            wait_for_cam(camera)

            # Start recording
            with camera.start_recording(
                    write_to_file=write_to_file,
                    filename=id) as stream:

                # Record for 2 seconds
                time.sleep(2)
                # Stop recording
                camera.stop_recording()

                # Check stream
                self.assertTrue(isinstance(stream.data, io.IOBase))
                self.assertTrue(isinstance(stream.binary, (bytes, bytearray)))

                # Check file
                if write_to_file:
                    statinfo = os.stat(stream.file)
                    self.assertTrue(statinfo.st_size > 0)

                # Log path
                temp_path = stream.file

            # Check file got deleted on __exit__
            self.assertFalse(os.path.isfile(temp_path))

            time.sleep(0.25)

    def test_video_store(self):
        """Tests recording videos to file on disk, without context manager."""
        global camera

        # Create unique ID
        id = uuid.uuid4().hex

        # Wait for camera
        wait_for_cam(camera)

        # Start recording
        stream = camera.start_recording(filename=id)
        # Record for 2 seconds
        time.sleep(2)
        # Stop recording
        camera.stop_recording()

        # Check file
        statinfo = os.stat(stream.file)
        self.assertTrue(statinfo.st_size > 0)

        # Ensure file deletion completes and returns True
        self.assertTrue(stream.delete())

        # Check file got deleted
        self.assertFalse(os.path.isfile(stream.file))


class TestThreadStarting(unittest.TestCase):
    def test_capture_restarting_stream(self):
        """Tests that a capture call restarts the camera worker thread."""
        global camera

        # Create unique ID
        id = uuid.uuid4().hex

        # Wait for camera
        wait_for_cam(camera)

        # Force-stop the camera worker thread (should return True)
        self.assertTrue(camera.stop_worker())

        # Check Pi camera has been disconnected
        self.assertFalse(camera.camera)

        # Restart worker thread by initialising a capture
        with camera.capture(
                use_video_port=True,
                filename=id) as stream:

            # Ensure StreamObject 'stream' has
            # a valid BytesIO object and byte string
            self.assertTrue(isinstance(stream.data, io.IOBase))
            self.assertTrue(isinstance(stream.binary, (bytes, bytearray)))


if __name__ == '__main__':
    camera = None
    with StreamingCamera() as camera:

        suites = [
            unittest.TestLoader().loadTestsFromTestCase(TestCaptureMethods),
            unittest.TestLoader().loadTestsFromTestCase(TestUnencodedMethods),
            unittest.TestLoader().loadTestsFromTestCase(TestThreadStarting),
            unittest.TestLoader().loadTestsFromTestCase(TestRecordMethods),
        ]

        alltests = unittest.TestSuite(suites)

        result = unittest.TextTestRunner(verbosity=2).run(alltests)

        if result.wasSuccessful():
            print(success_string)

    camera.close()
