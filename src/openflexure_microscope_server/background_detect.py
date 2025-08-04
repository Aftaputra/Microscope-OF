"""Provide functionality to detect if the camera is imaging sample or background.

An example background image is captured by the camera and sent to classes in the module
for analysis. Information from these images is used to detect whether an image from the
current camera field of view contains sample.
"""

from typing import Optional, Any
import cv2
import numpy as np
from pydantic import BaseModel, Field, ConfigDict
from pydantic.errors import PydanticUserError
from scipy.stats import norm
from labthings_fastapi.thing_description import type_to_dataschema


class MissingBackgroundDataError(RuntimeError):
    """An error raised if checking for sample without background data set."""


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
    settings: dict[str, Any]
    """The settings for the current background detect Algorithm. These are a dictionary
    dumped from the base model."""

    # Setting schema is a dict until LabThings FastAPI issue #154 is fixed and
    # DataSchema can be used directly. For now `model_dump()` must be used to dump schema
    # to a dict.
    settings_schema: dict[str, Any]
    """The schema for the settings for the current background detect Algorithm.

    This is reported so that the UI can dynamically create a UI for any background detector
    algorithm.
    """


class BackgroundDetectAlgorithm:
    """The base class for defining background detect algorithms."""

    background_data_model: BaseModel = BaseModel
    """The data model of the background data. This must be set by child classes"""
    settings_data_model: BaseModel = BaseModel
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
            settings=self.settings.model_dump(),
            # Dump model with `model_dump()` for reason explained when defining
            # BackgroundDetectorStatus
            settings_schema=type_to_dataschema(self.settings_data_model).model_dump(),
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
        """Set the statistics for the background image.

        This should be None, of no data is available. It can be set from either
        a dictionary or a base model of the type specified in
        ``self.background_data_model``.
        """
        try:
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
        except PydanticUserError as e:
            raise NotImplementedError(
                "BackgroundDetectAlgorithms must set their own background data model."
            ) from e

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

    model_config = ConfigDict(extra="forbid")

    channel_tolerance: float = 7.0
    """Channel Tolerance

    The number of standard deviations a pixel value must be from the background mean
    to be considered sample.
    """

    # Use Field to set Title reported to UI. By default Pydantic will convert the name
    # from snake_case to Title Case.
    min_sample_coverage: float = Field(25, title="Sample Coverage Required (%)")
    """Sample Coverage Required (%)

    The minimum percentage of the image that needs to be identified as sample for the
    image to be labeled as containing sample.
    """


class ColourChannelDetectLUV(BackgroundDetectAlgorithm):
    """Compare images with a known background in LUV colourspace.

    This uses an LUV colour space checking only the mean and standard deviation of the
    U and V channels. The LUV colourspace as it collect colours together in a human-
    intuitive way.
    """

    background_data_model: BaseModel = ChannelDistributions
    settings_data_model: BaseModel = ColourChannelDetectSettings

    def background_mask(self, image: np.ndarray) -> np.ndarray:
        """Calculate a binary image, showing whether each pixel is background.

        True is background.

        The image should be in LUV format, the output will be binary with the
        same shape in the first two dimensions.
        """
        if not self.background_data:
            raise MissingBackgroundDataError(
                "Background is not set: you need to calibrate background detection."
            )

        # The ``[1:]`` selects only the U and V channels of the image.
        # Only U and V are used as brightness (L) often changes as
        # the height of the sample changes.
        # Wrapping in ``[[ ]]`` forces the colour channels to the numpy axis 2
        # (3rd axis) so they are compared to the colour channel of each pixel.
        means = np.array([[self.background_data.means[1:]]])
        stds = np.array([[self.background_data.standard_deviations[1:]]])

        # Compare each image in the pixel with the mean and standard deviation along
        # axis to (the colour channels).
        return np.all(
            np.abs(image[:, :, 1:] - means) < stds * self.settings.channel_tolerance,
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

        return (1 - np.count_nonzero(mask) / np.prod(mask.shape)) * 100

    def image_is_sample(self, image: np.ndarray) -> tuple[bool, str]:
        """Label the current image as either background or sample.

        :returns: A tuple of the result (boolean), and explanation string. The
            explanation string is formatted so it can be added into a sentence such as
            ``An action was taken because the image is {message}.``
        """
        sample_coverage = self.get_sample_coverage(image)

        # Use bool otherwise get numpy variants of True and False.
        is_sample = bool(sample_coverage > self.settings.min_sample_coverage)
        message = f"{sample_coverage:0.1f}% sample"
        if not is_sample:
            message = "only " + message
        return is_sample, message

    def set_background(self, image: np.ndarray) -> None:
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
