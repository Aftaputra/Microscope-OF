"""Test the scan planning algorithms of the Microscope.

As well as low level function by function tests, this test suite also provides tests
that simulate scanning a sample, checking that the expected path is followed.
"""

import re

import pytest
from pydantic import BaseModel
import numpy as np

# Just for testing importing as
from openflexure_microscope_server.background_detect import (
    MissingBackgroundData,
    BackgroundDetectorStatus,
    BackgroundDetectAlgorithm,
    ChannelDistributions,
    ColourChannelDetectSettings,
    ColourChannelDetectLUV
)

RNG = np.random.default_rng()
IMG_SHAPE = (820, 616, 3)
BG_COLOR = [220, 215, 217]

PERC_REGEX = re.compile(r"(\d+\.+\d)+%")

@pytest.fixture
def background_image():
    image = np.ones(IMG_SHAPE, dtype=np.int16)
    image[:, :, 0] *= BG_COLOR[0]
    image[:, :, 1] *= BG_COLOR[1]
    image[:, :, 2] *= BG_COLOR[2]
    image += RNG.normal(scale=3, size=IMG_SHAPE).astype("int16")
    image[image < 0] = 0
    image[image > 255] = 255
    return image.astype("uint8")

@pytest.fixture
def sample_image(background_image):
    image = background_image.copy()
    x_cent = IMG_SHAPE[0]//2
    image[:x_cent,:,0] -= 180
    return image


def test_bg_detect_base_class():
    """Test the base class for background detect.

    If initialised as is it should raise not implemented error.
    """
    with pytest.raises(NotImplementedError):
        BackgroundDetectAlgorithm()

def test_partial_base_class(background_image):
    """Create a partial class so to initialise the base class and test other methods.

    This test is to check that if the necessary methods are not set, that an
    appropriate error is raise.
    """
    class BadAlgo1(BackgroundDetectAlgorithm):
        """Only has a settings model so it can initialise."""

        settings_data_model: BaseModel = ColourChannelDetectSettings

    bad_algo1 = BadAlgo1()
    status = bad_algo1.status
    assert not status.ready
    assert isinstance(status.settings, ColourChannelDetectSettings)

    with pytest.raises(NotImplementedError):
        # Should error on any dictionary input. This simulates loading settings from
        # disk
        bad_algo1.background_data = {"key": 1}

    with pytest.raises(NotImplementedError):
        bad_algo1.set_background(background_image)

    with pytest.raises(NotImplementedError):
        bad_algo1.image_is_sample(background_image)

def test_colour_channel_luv(background_image, sample_image):
    cc_luv = ColourChannelDetectLUV()

    # No background data so it is not ready and will error if image_is_sample is called.
    assert not cc_luv.status.ready
    with pytest.raises(MissingBackgroundData):
        cc_luv.image_is_sample(background_image)

    # Set the background
    cc_luv.set_background(background_image)
    # Now it is ready
    assert cc_luv.status.ready
    sample, message = cc_luv.image_is_sample(background_image)
    assert not sample
    assert "0.0%" in message
    sample, message = cc_luv.image_is_sample(sample_image)
    assert sample
    match = PERC_REGEX.search(message)
    assert match is not None
    # Should be 50% background. Allowing 49.8-50.2% due to noise.
    assert 49.8 < float(match.group(1)) < 50.2


# TODO Save data and reload it.