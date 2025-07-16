
import cv2
import numpy as np
from pydantic import BaseModel

class ChannelDistributions(BaseModel):
    """A BaseModel for storing the channel distribution of a background image."""

    means: list[float]
    """The mean of each channel in the colourspace."""
    standard_deviations: list[float]
    """The standard deviation of each channel in the colourspace."""
    colorspace: str = "LUV"
    """The colourspace used."""


class BackgroundDetectLUV:
    """Compare images with a known background in LUV colourspace.

    This uses an LUV colour space checking only the mean and standard deviation of the
    U and V channels. The LUV colourspace as it collect colours together in a
    """
    background_distributions: Optional[ChannelDistributions] = None
    background_tolerance: float = 7.0
    min_sample_coverage: float = 25.0

    def background_mask(self, image: np.ndarray) -> np.ndarray:
        """Calculate a binary image, showing whether each pixel is background.

        The image should be in LUV format, the output will be binary with the
        same shape in the first two dimensions.

        # human-intuitive way
        """
        d = self.background_distributions
        if not d:
            raise RuntimeError(
                "Background is not set: you need to calibrate background detection."
            )

        # Only use the U and V channels of as brightness (L) often changes as the
        # height of the sample changes.
        return np.all(
            np.abs(image[:, :, 1:] - np.array(d.means[1:])[np.newaxis, np.newaxis, :])
            < np.array(d.standard_deviations[1:])[np.newaxis, np.newaxis, :]
            * self.background_tolerance,
            axis=2,
        )

    def get_sample_coverage(self, image: np.ndarray) -> float:
        """Measure what percentage of the current image is background.

        * Acquire a new image from the preview stream,
        * Evaluate whether it is foreground or background, by comparing it to the saved
            statistics for a background image on a per-pixel basis
        * Returned value (between 0 and 100) is the percentage of the image that is
            background.
        """
        image_luv = cv2.cvtColor(image, cv2.COLOR_RGB2LUV)
        mask = self.background_mask(image_luv)
        return (1 - np.count_nonzero(mask) / np.prod(mask.shape)) * 100


    def image_is_sample(self, image: np.ndarrayl) -> bool:
        """Label the current image as either background or sample."""
        sample_coverage = self.get_sample_coverage(image)
        fraction_threshold = self.fraction

        return sample_coverage > self.min_sample_coverage


    def set_background(self, image: np.ndarray) -> np.ndarray:

        image_luv = cv2.cvtColor(image, cv2.COLOR_RGB2LUV)

        ch1 = (image_luv.T[0]).flatten()
        ch2 = (image_luv.T[1]).flatten()
        ch3 = (image_luv.T[2]).flatten()

        points = np.array([np.asarray(ch1), np.asarray(ch2), np.asarray(ch3)]).T

        # Get the mean and standard deviation of values in each channel
        mu, std = np.apply_along_axis(norm.fit, 0, points)

        self.background_distributions = ChannelDistributions(
            means=mu.tolist(),
            standard_deviations=std.tolist(),
            colorspace="LUV",
        )
