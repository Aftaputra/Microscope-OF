"""Test data collection from the Raspberry Picamera."""

import csv
import time

import numpy as np
from PIL import Image


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


def test_record_framerate_async(picamera_client, tmp_path):
    """Check that asynchronous framerate recording creates a valid CSV log."""
    output_dir = tmp_path / "framerate"

    returned_dir = picamera_client.record_framerate_async(
        duration=1.0,
        output_dir=str(output_dir),
    )

    assert returned_dir == str(output_dir)

    # Wait slightly longer than recording duration for thread completion
    time.sleep(1.5)

    log_files = list(output_dir.glob("framerate_log_*.csv"))

    # Ensure exactly one log file was created
    assert len(log_files) == 1

    log_file = log_files[0]

    # Ensure file is not empty
    assert log_file.stat().st_size > 0

    with open(log_file, newline="") as f:
        rows = list(csv.reader(f))

    # Header exists
    assert rows[0] == ["timestamp", "frame_count", "instant_fps"]

    # At least one FPS sample row exists
    assert len(rows) > 1

    # Validate sample row structure
    sample_row = rows[1]
    assert len(sample_row) == 3

    # Ensure FPS is positive
    fps = float(sample_row[2])
    assert fps > 0
