"""Test data collection from the Raspberry Picamera."""

import json
import time
from pathlib import Path

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


def test_record_framerate_async(picamera_client):
    """Check that asynchronous framerate monitoring creates a valid JSON log."""
    returned_dir = Path(picamera_client.record_framerate_async(duration=1.0))

    # Wait slightly longer than recording duration for async task completion
    time.sleep(1.5)

    log_files = list(returned_dir.glob("framerate_*.json"))

    # Ensure exactly one log file was created
    assert len(log_files) == 1

    log_file = log_files[0]

    # Ensure file is not empty
    assert log_file.stat().st_size > 0

    # Load JSON
    with open(log_file, "r") as f:
        data = json.load(f)

    assert "summary" in data
    assert "samples" in data

    summary = data["summary"]
    samples = data["samples"]

    assert "total_duration" in summary
    assert "total_frames" in summary
    assert "avg_fps" in summary

    assert summary["total_duration"] > 0
    assert summary["total_frames"] > 0
    assert summary["avg_fps"] > 0

    assert len(samples) > 0

    sample = samples[0]

    # Each sample row equivalent
    assert "timestamp" in sample
    assert "frame_count" in sample
    assert "frame_size_bytes" in sample
    assert "instant_fps" in sample

    assert sample["timestamp"] > 0
    assert sample["frame_count"] > 0
    assert sample["frame_size_bytes"] > 0

    assert samples[-1]["frame_count"] > 0
