"""Test data collection from the Raspberry Picamera."""

from PIL import Image
import numpy as np


def test_jpeg_and_array(picamera_client):
    """Check that a jpeg grabbed from the stream is the same size as other captures.

    Compare it to an array capture and a jpeg capture.
    """
    # Grab a jpeg from the stream
    blob = picamera_client.grab_jpeg()
    mjpeg_frame = Image.open(blob.open())
    # Verify throws an error if there are issues with the image
    mjpeg_frame.verify()
    assert mjpeg_frame.format == "JPEG"

    # Capture a jpeg
    blob = picamera_client.capture_jpeg(stream_name="main")
    jpeg_capture = Image.open(blob.open())
    jpeg_capture.verify()
    assert jpeg_capture.format == "JPEG"

    # Capture an array
    arrlist = picamera_client.capture_array(stream_name="main")
    array_main = np.array(arrlist)

    # Verify image sizes are the same
    assert mjpeg_frame.size == jpeg_capture.size
    assert array_main.shape[1::-1] == jpeg_capture.size
