"""Check exposure times do not drift.

This can get very tedious. Recommend running pytest with -s option
to monitor progress.
"""

import logging
import time

from fastapi.testclient import TestClient

from labthings_fastapi.server import ThingServer
from labthings_fastapi.client import ThingClient

from openflexure_microscope_server.things.camera.picamera import StreamingPiCamera2

logging.basicConfig(level=logging.DEBUG)

# The tolerance used to be a setting of the camera, and any changes within tolerance
# were ignored. Now this isn't needed we always set a value 1 larger than the last
# accepted value as the PiCamera always rounds down.
# The tolerance is needed in this test as when setting an arbitrary value it is rounded
# down to a hardware compatible one.
EXPOSURE_TOL = 30


def _test_exposure_time_drift(desired_time):
    """Capture 10 full res images and check that the exposure time remains constant.

    This confirms that automatic exposure time adjustment is fully turned off during
    capture.
    """
    cam = StreamingPiCamera2()
    server = ThingServer()
    server.add_thing(cam, "/camera/")

    with TestClient(server.app) as test_client:
        client = ThingClient.from_url("/camera/", client=test_client)
        client.exposure_time = desired_time
        print(f"Setting desired time of {desired_time}")
        time.sleep(0.5)
        pre_capture_et = client.exposure_time
        print(f"Pre-capture the time is set to {pre_capture_et}")
        # Check exp is set correctly within known tolerance
        assert abs(pre_capture_et - desired_time) < EXPOSURE_TOL

        for i in range(10):
            client.capture_jpeg(resolution="full")
            if i == 0:
                # Exposure can update on first capture, due to frame rate restrictions
                first_et = client.exposure_time
                assert abs(first_et - desired_time) < EXPOSURE_TOL
            else:
                frame_et = client.exposure_time
                print(f"Frame {i} captured with exposure time {frame_et}")
                # Check no further drift in value
                assert first_et == frame_et

        # Set the exposure time to the value it already is. To check it doesn't shift
        print(f"Setting exposure time to {frame_et} to check it doesn't change")
        client.exposure_time = frame_et
        time.sleep(0.5)
        # Check before and after capture
        assert client.exposure_time == frame_et
        client.capture_jpeg(resolution="full")
        assert client.exposure_time == frame_et
        print("Exposure time didn't change!!")
    print(f"End of test for exposure target {desired_time}")


def test_exposure_time_drift():
    """Performs the exposure time test for a range of exposure time values."""
    for desired_time in [100, 1000, 10000]:
        _test_exposure_time_drift(desired_time)


def test_exposure_time_on_start_and_stop_stream():
    """Capture 10 full res images and check that the exposure time remains constant.

    This confirms that automatic exposure time adjustment is fully turned off during
    capture.
    """
    cam = StreamingPiCamera2()
    server = ThingServer()
    server.add_thing(cam, "/camera/")
    desired_time = 1000
    # Create a test client
    with TestClient(server.app) as test_client:
        client = ThingClient.from_url("/camera/", client=test_client)
        # Set a desired exposure time
        client.exposure_time = desired_time
        print(f"Setting desired time of {desired_time}")
        time.sleep(0.5)
        # Take a couple of images to make sure that the exposure is adjusted to
        # a hardware compatible value.
        for i in range(2):
            client.capture_jpeg(resolution="full")
        # Save this time.
        set_time = client.exposure_time
        assert abs(set_time - desired_time) < EXPOSURE_TOL

        # Mimick doing 10 smart scans. Change to full res, take some images. Return
        # to standard preview resolution.
        for i in range(10):
            print(f"Starting simulation scan {i}")
            # This will need updating if we start supporting other Picamera models
            # It is currently used here to mimick the behaviour in in scanning.
            client.start_streaming(main_resolution=(3280, 2464))
            time.sleep(0.5)
            for _j in range(5):
                client.capture_to_memory(buffer_max=1)
            # Reset to main resolution
            time.sleep(0.5)
            client.start_streaming()
        # Check after all of this the exposure time is the same.
        assert abs(client.exposure_time - set_time) < EXPOSURE_TOL
