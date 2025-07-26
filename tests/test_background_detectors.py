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
    MissingBackgroundDataError,
    BackgroundDetectAlgorithm,
    ChannelDistributions,
    ColourChannelDetectSettings,
    ColourChannelDetectLUV,
)

RNG = np.random.default_rng()
IMG_SHAPE = (820, 616, 3)
BG_COLOR = [220, 215, 217]

PERC_REGEX = re.compile(r"(\d+\.+\d)+%")


@pytest.fixture
def background_image():
    """Generate a numpy array that simulates a background image."""
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
    """Generate a numpy array of a simulated image where 50% is a block of red."""
    image = background_image.copy()
    x_cent = IMG_SHAPE[0] // 2
    image[:x_cent, :, 0] -= 180
    return image


def test_bg_detect_base_class():
    """Test the base class for background detect.

    If initialised as is it should raise not implemented error.
    """
    with pytest.raises(NotImplementedError):
        BackgroundDetectAlgorithm()


def test_partial_base_class(background_image):
    """Create a partial class to initialise the base class and test other methods.

    This test is to check that if the necessary methods are not set, that an
    appropriate error is raised.
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
    """Test measuring if a sample is background."""
    cc_luv = ColourChannelDetectLUV()

    # No background data so it is not ready and will error if image_is_sample is called.
    assert not cc_luv.status.ready
    with pytest.raises(MissingBackgroundDataError):
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

    # Require 75% coverage
    cc_luv.settings = ColourChannelDetectSettings(min_sample_coverage=75.0)

    sample, message = cc_luv.image_is_sample(sample_image)
    # No longer detected as a sample.
    assert not sample
    match = PERC_REGEX.search(message)
    assert match is not None
    # Still 50% background.
    assert 49.8 < float(match.group(1)) < 50.2


def test_colour_channel_luv_save_load(background_image, sample_image):
    """Get settings and data as dicts, and creating new instance using these dicts.

    This is how the camera will load/save settings from/to disk.
    """
    cc_luv = ColourChannelDetectLUV()
    cc_luv.set_background(background_image)

    # Check types for background data
    assert cc_luv.background_data_model is ChannelDistributions
    assert isinstance(cc_luv.background_data, cc_luv.background_data_model)
    # Change Settings
    cc_luv.settings = ColourChannelDetectSettings(min_sample_coverage=10.0)

    setting_dict = cc_luv.settings.model_dump()
    data_dict = cc_luv.background_data.model_dump()

    # Remove the old detector so we don't accidentally use it!
    del cc_luv

    # Create a new instance
    cc_luv2 = ColourChannelDetectLUV()
    assert not cc_luv2.status.ready
    # Load settings and channels from dictionary as the camera will do on init.
    cc_luv2.settings = setting_dict
    cc_luv2.background_data = data_dict

    # Now should be ready to use
    assert cc_luv2.status.ready
    assert cc_luv2.settings.min_sample_coverage == 10.0
    sample, _ = cc_luv2.image_is_sample(sample_image)
    assert sample

    # One final test that None can be set explicitly to background data as this will
    # happen if loading with background detect not saved.
    cc_luv3 = ColourChannelDetectLUV()
    assert not cc_luv3.status.ready
    # Load settings and channels from dictionary as the camera will do on init.
    cc_luv3.settings = setting_dict
    cc_luv3.background_data = None
    # Still not ready
    assert not cc_luv3.status.ready


def test_colour_channel_luv_load_bad_data():
    """Check a type error is thrown on bad data input."""

    class WrongModel(BaseModel):
        """Using a different BaseModel as this is most likely to cause confusion."""

        prop1: int = 8
        prop2: str = "foo"

    cc_luv = ColourChannelDetectLUV()
    with pytest.raises(TypeError):
        cc_luv.settings = WrongModel()
    with pytest.raises(TypeError):
        cc_luv.background_data = WrongModel()
