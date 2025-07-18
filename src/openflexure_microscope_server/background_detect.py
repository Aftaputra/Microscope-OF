"""Provide functionality to detect if the camera is imaging sample or background.

An example background image is captured by the camera and sent to classes in the module
for analysis. Information from this images is used to detect whether an image from the
current camera field of view contains sample.
"""

from typing import Optional, Any
import cv2
import numpy as np
from pydantic import BaseModel
from pydantic.errors import PydanticUserError
from scipy.stats import norm
from labthings_fastapi.thing_description import type_to_dataschema


class BackgroundDetectorStatus(BaseModel):
    """The status information about a background detector instance needed for the GUI.

    Each BackgroundDetectAlgorithm must be able to return one of these models when
    ``status`` is called.
    """

    ready: bool
    """True if ready to be used, if False this detector isn't initialised for use.

    This could be called ``has_background_data`` or similar, but the more generic
    ``ready`` is used in case more complex methods are added in the future, which
    need different initialisation.
    """
    settings: BaseModel
    """The settings for this this background detect Algorithm"""
    settings_schema: dict[str, Any]


class BackgroundDetectAlgorithm:
    """The base class for defining background detect algorithms."""

    background_data_model: BaseModel
    """The data model of the background data. This must be set by child classes"""
    settings_data_model: BaseModel
    """The data model of algorithm settings. This must be set by child classes"""

    def __init__(self):
        """Initialise the algorithm settings."""
        try:
            self._settings: BaseModel = self.settings_data_model()
        except PydanticUserError as e:
            raise NotImplementedError(
                "BackgroundDetectAlgorithms must set their own settings data model."
            ) from e

    @property
    def status(self) -> BackgroundDetectorStatus:
        """The status information needed for the GUI. Read only."""
        return BackgroundDetectorStatus(
            ready=self.background_data is not None,
            settings=self.settings,
            settings_schema=type_to_dataschema(self.settings_data_model),
        )

    # Requires a getter and a setter to support being a BaseModel but being
    # saved to file as a dict
    _background_data: Optional[BaseModel] = None

    @property
    def background_data(self) -> Optional[BaseModel]:
        """The statistics of the background image."""
        bd = self._background_data
        if bd is None:
            return None
        return bd

    @background_data.setter
    def background_data(self, value: Optional[BaseModel | dict]) -> None:
        if value is None:
            self._background_data = None
        elif isinstance(value, self.background_data_model):
            self._background_data = value
        elif isinstance(value, dict):
            self._background_data = self.background_data_model(**value)
        else:
            raise TypeError(
                f"Cannot set background_data with an object of type {type(value)}"
            )

    @property
    def settings(self) -> BaseModel:
        """The statistics of the background image."""
        return self._settings

    @settings.setter
    def settings(self, value: BaseModel | dict) -> None:
        if isinstance(value, self.settings_data_model):
            self._settings = value
        elif isinstance(value, dict):
            self._settings = self.settings_data_model(**value)
        else:
            raise TypeError(f"Cannot set settings with an object of type {type(value)}")

    def image_is_sample(self, image: np.ndarray) -> tuple[bool, str]:
        """Label the current image as either background or sample.

        :returns: A tuple of the result (boolean), and explanation string. The
            explanation string is formatted so it can be added into a sentence such as
            ``An action was taken because the image is {message}.``
        """
        raise NotImplementedError(
            "Each background detect algorithm must implement an image_is_sample method."
        )

    def set_background(self, image: np.ndarray) -> BaseModel:
        """Use the input image to update the background data.

        Background data must be a Pydantic BaseModel.
        """
        raise NotImplementedError(
            "Each background detect algorithm must implement an set_background method."
        )


class ChannelDistributions(BaseModel):
    """A BaseModel for storing the channel distribution of a background image."""

    means: list[float]
    """The mean of each channel in the colourspace."""
    standard_deviations: list[float]
    """The standard deviation of each channel in the colourspace."""


class ColourChannelDetectSettings(BaseModel):
    """A BaseModel for storing the settings for colour channel detectors."""

    channel_tolerance: float = 7.0
    """Channel Tolerance

    The number of standard deviations a pixel value must be from the background mean
    to be considered sample.
    """
    min_sample_coverage: float = 25.0
    """Sample Coverage Required (%)

    The minimum percentage of the image that needs to be identified as sample for the
    image to be labeled as containing sample.
    """


class ColourChannelDetectLUV(BackgroundDetectAlgorithm):
    """Compare images with a known background in LUV colourspace.

    This uses an LUV colour space checking only the mean and standard deviation of the
    U and V channels. The LUV colourspace as it collect colours together in a
    """

    background_data_model: BaseModel = ChannelDistributions
    settings_data_model: BaseModel = ColourChannelDetectSettings

    def background_mask(self, image: np.ndarray) -> np.ndarray:
        """Calculate a binary image, showing whether each pixel is background.

        True is background.

        The image should be in LUV format, the output will be binary with the
        same shape in the first two dimensions.
        """
        d = self.background_data
        if not d:
            raise RuntimeError(
                "Background is not set: you need to calibrate background detection."
            )
        print(d)
        # Only use the U and V channels of as brightness (L) often changes as the
        # height of the sample changes.
        return np.all(
            np.abs(image[:, :, 1:] - np.array(d.means[1:])[np.newaxis, np.newaxis, :])
            < np.array(d.standard_deviations[1:])[np.newaxis, np.newaxis, :]
            * self.settings.channel_tolerance,
            axis=2,
        )

    def get_sample_coverage(self, image: np.ndarray) -> float:
        """Return the percentage of the input image that is background.

        Evaluate whether it is foreground or background by comparing it to the saved
        statistics for a background image on a per-pixel basis

        :returns: A value (between 0 and 100) is the percentage of the image that is
            sample.
        """
        image_luv = cv2.cvtColor(image, cv2.COLOR_RGB2LUV)
        mask = self.background_mask(image_luv)
        print(np.count_nonzero(mask))
        print(np.prod(mask.shape))
        print((1 - np.count_nonzero(mask) / np.prod(mask.shape)) * 100)
        return (1 - np.count_nonzero(mask) / np.prod(mask.shape)) * 100

    def image_is_sample(self, image: np.ndarray) -> tuple[bool, str]:
        """Label the current image as either background or sample.

        :returns: A tuple of the result (boolean), and explanation string. The
            explanation string is formatted so it can be added into a sentence such as
            ``An action was taken because the image is {message}.``
        """
        sample_coverage = self.get_sample_coverage(image)

        is_sample = sample_coverage > self.settings.min_sample_coverage
        message = f"{sample_coverage}% sample"
        if not is_sample:
            message = "only " + message
        return is_sample, message

    def set_background(self, image: np.ndarray) -> ChannelDistributions:
        """Use the input image to update the background distributions."""
        image_luv = cv2.cvtColor(image, cv2.COLOR_RGB2LUV)

        ch1 = (image_luv.T[0]).flatten()
        ch2 = (image_luv.T[1]).flatten()
        ch3 = (image_luv.T[2]).flatten()

        points = np.array([np.asarray(ch1), np.asarray(ch2), np.asarray(ch3)]).T

        # Get the mean and standard deviation of values in each channel
        mu, std = np.apply_along_axis(norm.fit, 0, points)

        self.background_data = ChannelDistributions(
            means=mu.tolist(), standard_deviations=std.tolist()
        )
