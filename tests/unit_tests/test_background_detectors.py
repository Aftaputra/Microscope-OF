"""Test the background detection algorithms.

This tests both the base class an individual algorithms.
"""

import re

import numpy as np
import pytest
from pydantic import BaseModel

from openflexure_microscope_server.background_detect import (
    BackgroundDetectAlgorithm,
    ChannelBlankError,
    ChannelDeviationLUV,
    ChannelDistributions,
    ColourChannelDetectLUV,
    ColourChannelDetectSettings,
    MissingBackgroundDataError,
    _chunked_stds,
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


def test_partial_base_classes():
    """Create a partial classes and check they raise the correct errors."""

    class BadAlgo1(BackgroundDetectAlgorithm):
        """Only has a settings model so it cannot initialise."""

        settings_data_model = ColourChannelDetectSettings

    with pytest.raises(NotImplementedError):
        BadAlgo1()

    class BadAlgo2(BackgroundDetectAlgorithm):
        """Only has a background model so it cannot initialise."""

        background_data_model = ChannelDistributions

    with pytest.raises(NotImplementedError):
        BadAlgo2()

    class BadAlgo3(BackgroundDetectAlgorithm):
        """Has both models, intalises by cannot run set_background or image_is_sample."""

        settings_data_model = ColourChannelDetectSettings
        background_data_model = ChannelDistributions

    bad_algo3 = BadAlgo3()

    with pytest.raises(NotImplementedError):
        bad_algo3.set_background(background_image)

    with pytest.raises(NotImplementedError):
        bad_algo3.image_is_sample(background_image)


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

    # Remove the 2nd detector so we don't accidentally use it!
    del cc_luv2

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


def create_patchwork_image(magnitude=3, blank_channels=None):
    """Create a patchwork image, with known stds per chunk.

    :return: The image, and the (8,8,3) array of stds
    """
    if blank_channels is None:
        blank_channels = []
    n_rows = 8
    n_cols = 8
    chunk_h = 10
    chunk_w = 10

    # Precompute chunk stds and construct the final image
    expected_stds = np.zeros((n_rows, n_cols, 3), dtype=float)
    img = np.zeros((n_rows * chunk_h, n_cols * chunk_w, 3), dtype=np.uint8)

    for i in range(n_rows):
        for j in range(n_cols):
            for channel in range(3):
                if channel in blank_channels:
                    chunk = np.zeros((chunk_h, chunk_w), dtype=np.uint8)
                else:
                    chunk = 9.8 * np.ones((chunk_h, chunk_w))
                    chunk += RNG.normal(scale=magnitude, size=(chunk_h, chunk_w))
                    chunk = chunk.astype(np.uint8)

                # Store its std
                expected_stds[i, j, channel] = np.std(chunk)

                # Insert chunk into the final large image
                y0, y1 = i * chunk_h, (i + 1) * chunk_h
                x0, x1 = j * chunk_w, (j + 1) * chunk_w
                img[y0:y1, x0:x1, channel] = chunk
    return img, expected_stds


def test_chunked_stds_with_precomputed_chunk_stds():
    """Test _chunked_stds returns the answer calculated when making a patchwork image."""
    img, expected_stds = create_patchwork_image()

    # Run the function under test
    result = _chunked_stds(img, n_rows=8, n_cols=8)

    # Compare
    np.testing.assert_allclose(result, expected_stds, rtol=1e-6, atol=1e-12)


def test_channel_deviation_luv_set_background(mocker):
    """Test set_background takes the median of each channel, and errors for blank channels."""
    cd_luv = ChannelDeviationLUV()

    # Patch RGB to LUV so or we don't know what the STDs should be
    mocker.patch("cv2.cvtColor", side_effect=lambda img, _method: img)

    for magnitude in [0.2, 1, 10]:
        # Create an image and set it as background
        img, expected_stds = create_patchwork_image(magnitude=magnitude)
        cd_luv.set_background(img)

        # Do a somewhat verbose checking for clarity
        for channel in range(3):
            # Saved std
            channel_std = cd_luv.background_data.standard_deviations[channel]
            # Expected median
            channel_median = np.median(expected_stds[:, :, channel])
            # If the median is above the minimum allowed then it should be returned
            if channel_median > cd_luv.min_stds[channel]:
                assert np.isclose(channel_std, channel_median, rtol=1e-6, atol=1e-12)
            else:
                # If not the minimum is returned.
                assert channel_std == cd_luv.min_stds[channel]

    # Also check that if channels are blank then an error is thrown
    img, _expected_stds = create_patchwork_image(magnitude=1, blank_channels=[1, 2])
    with pytest.raises(ChannelBlankError):
        cd_luv.set_background(img)


def test_channel_deviation_luv_image_is_sample(background_image, mocker):
    """Check image_is_sample reports the result from get_sample_coverage."""
    cd_luv = ChannelDeviationLUV()

    # No background data so it is not ready and will error if image_is_sample is called.
    assert not cd_luv.status.ready
    with pytest.raises(MissingBackgroundDataError):
        cd_luv.image_is_sample(background_image)

    cd_luv.settings.min_sample_coverage = 20
    cd_luv.get_sample_coverage = mocker.Mock(return_value=10)
    is_sample, message = cd_luv.image_is_sample(background_image)
    assert not is_sample
    assert message == r"only 10.0% sample"

    # Reduce the min coverage
    cd_luv.settings.min_sample_coverage = 9

    is_sample, message = cd_luv.image_is_sample(background_image)
    assert is_sample
    assert message == r"10.0% sample"


def test_channel_deviation_luv_get_sample_coverage(background_image, mocker):
    """Check _get_sample_coverage returns the values expected."""
    cd_luv = ChannelDeviationLUV()

    # Create fake chunked STD data where each channel is the numbers 0 -> 31.5 in 0.5
    # steps
    grid = np.arange(0, 32, 0.5).reshape(8, 8)
    fake_stds = np.stack([grid, grid, grid], axis=-1)
    mocker.patch(
        "openflexure_microscope_server.background_detect._chunked_stds",
        return_value=fake_stds,
    )

    # Create fake background
    cd_luv.background_data = ChannelDistributions(
        means=[0, 0, 0], standard_deviations=[1.1, 1.1, 1.1]
    )
    # Get sample coverage with channel tolerance of 7. Checking each channel for the
    # numbers below 7.7. There are 16 out of 64. So 75% should be sample
    cd_luv.settings.channel_tolerance = 7
    assert cd_luv.get_sample_coverage(background_image) == 75
    # This is unchanged if two channels have larger background values.
    cd_luv.background_data = ChannelDistributions(
        means=[0, 0, 0], standard_deviations=[1.6, 1.6, 1.1]
    )
    assert cd_luv.get_sample_coverage(background_image) == 75
    # But coverage increases if any channels has a lower background value.
    cd_luv.background_data = ChannelDistributions(
        means=[0, 0, 0], standard_deviations=[1.6, 0.6, 1.1]
    )
    assert cd_luv.get_sample_coverage(background_image) == 85.9375
    # Returns to 75% if that channel is empty
    fake_stds[:, :, 1] = 0
    assert cd_luv.get_sample_coverage(background_image) == 75
