"""Use the Simulated camera to test base camera functionality.

For tests of functionality specific to the simulated camera see
test_simulated_camera.py and for testing the consistency of camera APIs see
test_cameras.py.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pytest
from PIL import Image

from openflexure_microscope_server.things import RelativeDataPath
from openflexure_microscope_server.things.camera import CaptureMode
from openflexure_microscope_server.things.camera.simulation import SimulatedCamera
from openflexure_microscope_server.things.stage.dummy import DummyStage

from ..shared_utils.lt_test_utils import LabThingsTestEnv


@pytest.fixture
def test_env() -> LabThingsTestEnv:
    """Yield a test environment with the Simulated Camera and Dummy Stage."""
    thing_conf = {"camera": SimulatedCamera, "stage": DummyStage}
    with LabThingsTestEnv(things=thing_conf) as env:
        yield env


def test_handle_broken_frame(test_env):
    """Monkey patch the the mjpeg steam so 1 in 5 frames are broken, then test operation.

    This simulates the very occasional broken frames that can occur when grabbing
    directly from the MJPEG stream.
    """
    camera = test_env.get_thing_by_type(SimulatedCamera)

    # Money patch the mjpeg_stream grab_frame to break 1 in 5 frames.
    frame_number = 0
    original_grabber = camera.mjpeg_stream.grab_frame

    async def flaky_grabber():
        """Break 1 in 5 frames."""
        # Use a non-local variable to know the frame count.
        nonlocal frame_number
        frame = await original_grabber()
        if frame_number % 5 == 2:
            # Make a weird broken frame
            frame = frame[:2000] + frame[:2000]
        frame_number += 1
        return frame

    camera.mjpeg_stream.grab_frame = flaky_grabber

    # Check that this does cause broken frames.
    # The noqa is because we don't know exactly when the error is thrown so we
    # can't have a single simple statement in the pytest raises.
    with pytest.raises(OSError, match="broken data stream when reading image file"):  # noqa PT012
        for _i in range(15):
            jpeg = camera.grab_jpeg()
            np.asarray(Image.open(jpeg.open()))

    # Check that grab_as_array handles the broken frames and completes without
    # the same error.
    for _i in range(15):
        array = camera.grab_as_array()
        assert isinstance(array, np.ndarray)


@dataclass
class MemorySaveTestCase:
    """Inputs and expected outputs for testing ``save_from_memory``.

    The default save kwargs assume a jpeg.
    """

    filename: str = "foobar.jpeg"
    save_resolution: Optional[tuple[int, int]] = None
    resize_needed: bool = False
    save_kwargs: dict[str, int] = field(
        default_factory=lambda: {"quality": 95, "subsampling": 0}
    )


SAVE_TEST_CASES = [
    # Default test case is a jpeg, ckec it works with all extensions.
    MemorySaveTestCase("foobar.jpeg"),
    MemorySaveTestCase("foobar.jpg"),
    MemorySaveTestCase("foobar.JPEG"),
    MemorySaveTestCase("foobar.JPG"),
    MemorySaveTestCase("foobar.png.jpeg"),
    MemorySaveTestCase("foobar.png", save_kwargs={}),
    MemorySaveTestCase("foobar.PNG", save_kwargs={}),
    MemorySaveTestCase("foobar.jpeg.png", save_kwargs={}),
    MemorySaveTestCase(save_resolution=None, resize_needed=False),
    MemorySaveTestCase(save_resolution=(1000, 1200), resize_needed=False),
    MemorySaveTestCase(save_resolution=(2000, 2400), resize_needed=True),
]


@pytest.mark.parametrize("test_case", SAVE_TEST_CASES)
def test_save_from_memory(test_case, test_env, mocker):
    """Check the correct timage is retrieved and saved with correct settings."""
    camera = test_env.get_thing_by_type(SimulatedCamera)
    camera._memory_buffer = mocker.Mock()
    camera._add_metadata_to_capture = mocker.Mock()

    mode = CaptureMode(description="foo", save_resolution=test_case.save_resolution)
    capture_modes_mock = mocker.PropertyMock(return_value={"standard": mode})
    mocker.patch.object(type(camera), "capture_modes", capture_modes_mock)

    mock_image = mocker.Mock()
    # Make resize return itself so we can track further calls of the Image object after
    # a resize
    mock_image.resize.return_value = mock_image
    mock_image.size = (1000, 1200)

    camera._memory_buffer.get_image.return_value = (
        mock_image,
        {"meta": "data"},
        "standard",
    )

    camera._data_dir = os.path.normpath("/fake/data/dir")

    camera.save_from_memory(RelativeDataPath(test_case.filename), 33)

    assert camera._memory_buffer.get_image.call_count == 1
    assert camera._memory_buffer.get_image.call_args.args == (33,)
    assert camera._add_metadata_to_capture.call_count == 1
    assert mock_image.resize.call_count == (1 if test_case.resize_needed else 0)
    assert mock_image.save.call_count == 1
    assert mock_image.save.call_args.kwargs == test_case.save_kwargs
