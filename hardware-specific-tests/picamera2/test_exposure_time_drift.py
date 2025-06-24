import logging
import time

from fastapi.testclient import TestClient

from labthings_fastapi.server import ThingServer
from labthings_fastapi.client import ThingClient

from openflexure_microscope_server.things.camera.picamera import StreamingPiCamera2

logging.basicConfig(level=logging.DEBUG)


def test_exposure_time_drift():
    """
    Capture 10 full resolution images and check that the exposure time remains constant

    This confirms that automatic exposure time adjustment is fully turned off
    """
    cam = StreamingPiCamera2()
    server = ThingServer()
    server.add_thing(cam, "/camera/")

    with TestClient(server.app) as test_client:
        client = ThingClient.from_url("/camera/", client=test_client)
        # 5444 is an exposure time supported by PiCamera2
        client.exposure_time = 5444
        time.sleep(0.5)
        initial_et = client.exposure_time
        print(f"Before capture, et is {client.exposure_time}")
        for i in range(5):
            client.capture_jpeg(resolution="full")
            print(f"After capture, et is {client.exposure_time}")
        final_et = client.exposure_time
        assert initial_et == final_et


if __name__ == "__main__":
    test_exposure_time_drift()
