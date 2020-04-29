"""
Camera-stage tracker

The `Tracker` class in this file is used to simplify code for tasks that involve moving the
stage, and tracking the corresponding motion with the camera.

(c) Richard Bowman 2019, released under GNU GPL v3
"""
import numpy as np
import time
from numpy.linalg import norm
import cv2
from scipy import ndimage
from collections import namedtuple
import logging
from fft_image_tracking import high_pass_fft_template, displacement_from_fft_template, TrackingError

TrackerHistory = namedtuple("TrackerHistory", ["stage_positions", "image_positions"])

def central_half(image):
    """Return the central 50% (in X and Y) of an image"""
    w, h = image.shape[:2]
    return image[int(w/4):int(3*w/4),int(h/4):int(3*h/4), ...]


def datum_pixel(image):
    """Get the datum pixel of an image - if no property is present, assume the central pixel."""
    try:
        return np.array(image.datum_pixel)
    except:
        return (np.array(image.shape[:2]) - 1) / 2.

########## Cross-correlation based tracking ############
def locate_feature_in_image(image, feature, margin=0, restrict=False, relative_to="top left"):
    """Find the given feature (small image) and return the position of its datum (or centre) in the image's pixels.

    image : numpy.array
        The image in which to look.
    feature : numpy.array
        The feature to look for.  Ideally should be an `ImageWithLocation`.
    margin : int (optional)
        Make sure the feature image is at least this much smaller than the big image.  NB this will take account of the
        image datum points - if the datum points are superimposed, there must be at least margin pixels on each side of
        the feature image.
    restrict : bool (optional, default False)
        If set to true, restrict the search area to a square of (margin * 2 + 1) pixels centred on the pixel that most
        closely overlaps the datum points of the two images.
    relative_to : string (optional, default "top left")
        We return the position of the centre (or datum pixel, if it's got that metadata) of the feature, relative to
        either the top left (i.e. 0,0) pixel in the image, or the central pixel - to do the latter, set ``relative_to``
        to "centre" (or "center" if you must).

    The `image` must be larger than `feature` by a margin big enough to produce a meaningful search area.  We use the
    OpenCV `matchTemplate` method to find the feature.  The returned position is the position, relative to the corner of
    the first image, of the "datum pixel" of the feature image.  If no datum pixel is specified, we assume it's the
    centre of the image.  The output of this function can be passed into the pixel_to_location() method of the larger
    image to yield the position in the sample of the feature you're looking for.
    """
    # The line below is superfluous if we keep the datum-aware code below it.
    assert image.shape[0] > feature.shape[0] and image.shape[1] > feature.shape[1], "Image must be larger than feature!"
    # Check that there's enough space around the feature image
    lower_margin = datum_pixel(image) - datum_pixel(feature)
    upper_margin = (image.shape[:2] - datum_pixel(image)) - (feature.shape[:2] - datum_pixel(feature))
    assert np.all(np.array([lower_margin, upper_margin]) >= margin), "The feature image is too large."
    #TODO: sensible auto-crop of the template if it's too large?
    image_shift = np.array((0,0))
    if restrict:
        # if requested, crop the larger image so that our search area is (2*margin + 1) square.
        image_shift = np.array(lower_margin - margin,dtype = int)
        image = image[image_shift[0]:image_shift[0] + feature.shape[0] + 2 * margin + 1,
                      image_shift[1]:image_shift[1] + feature.shape[1] + 2 * margin + 1, ...]

    corr = cv2.matchTemplate(image, feature,
                             cv2.TM_SQDIFF_NORMED)  # correlate them: NB the match position is the MINIMUM
    corr = -corr # invert the image so we can find a peak
    corr += (corr.max() - corr.min()) * 0.1 - corr.max()  # background-subtract 90% of maximum
    corr = cv2.threshold(corr, 0, 0, cv2.THRESH_TOZERO)[
        1]  # zero out any negative pixels - but there should always be > 0 nonzero pixels
    assert np.sum(corr) > 0, "Error: the correlation image doesn't have any nonzero pixels."
    peak = ndimage.measurements.center_of_mass(corr)  # take the centroid (NB this is of grayscale values, not binary)
    pos = np.array(peak) + image_shift + datum_pixel(feature) # return the position of the feature's datum point.
    if relative_to in ["top left", None]:
        return pos
    if relative_to in ["centre", "center"]:
        return pos - (np.array(image.shape[:2]) - 1)/2.
    raise ValueError("An invalid value was specified for datum.")
    
######## FFT based tracking functions ###########
# moved to fft_image_tracking.py

class Tracker():
    def __init__(self, grab_image, get_position, settle=None, method="direct", **kwargs):
        """A class to manage moving the stage and following motion in the image
        
        Constructor Arguments:
            grab_image: a function that returns the image as a numpy array
            get_position: a function that returns position as a numpy array
            settle: a function that waits and/or discards images
            method: string, currently "direct" (default) or "fft"
            Additional keyword arguments are passed to the tracking method.
            
        Tracking methods:
            "direct": uses cross-correlation with the central half of the image.  
                There are currently no options for this method.
            "fft" uses FFT-based cross-correlation, after a high pass filter.  
                Keyword arguments are accepted:
                    pad: boolean, default=True
                        Whether to zero-pad the FFT to remove ambiguity.  If 
                        false, the answer is only unique modulo one field of
                        view due to the periodic nature of FFTs.  Setting this
                        option to False speeds up tracking by about 4x.
                    sigma: floating point, default=10
                        The standard deviation, in pixels, of a Gaussian filter
                        used to smooth the image, before subtracting the smooth
                        image from the original, in a low pass filter.  NB the
                        standard deviation is given in pixels, but is applied
                        in the Fourier domain (with appropriate transformation).
                        The value of sigma does not affect computation speed.
            
        We accept functions because that seems like the easiest way to be
        compatible with many different cameras/stages.  Subclass and override
        ``__init__`` if you want to use a particular object instead.

        # Subclassing notes
        If you change the tracking method, you should override:
            * track_image
            * generate_template
            * max_displacement
            * min_displacement (optional - defaults to -max_displacment)

        NB the ``image_position`` that this class returns may be the negative of 
        what you might expect.  This is because normally we are looking for 
        where a certain object (usually matched to a template image) is within
        an image.  Instead, the ``Tracker`` is following motion of the image
        relative to a template.  Our model is that we have a static image on
        the slide, so we're tracking the slide's motion.
        """
        self._grab_image = grab_image
        self._get_position = get_position
        self._settle = settle
        self._template = None
        self.margin = np.array([0, 0])
        self._template_position = np.array([0.0, 0.0])
        self._last_point = None
        self.image_shape = None
        self.method = method
        #self.kwargs = {"error_threshold": 0.2}.update(kwargs)
        self.kwargs = kwargs
    
    def get_position(self):
        """Get the position of the stage"""
        return np.array(self._get_position())
    
    def settle(self):
        """Wait a short time and discard an image so the stage is no longer wobbling."""
        if self._settle is not None:
            self._settle()
        else:
            time.sleep(0.3)
            self._grab_image()
            
    @property
    def template(self):
        """The template image (should be a numpy array)"""
        if self._template is None:
            raise ValueError("Attempt to use the tracker before setting the template")
        else:
            return self._template
        
    @template.setter
    def template(self, new_value):
        self._template = new_value
        
    def acquire_template(self, settle=True, reset_history=True, relative_positions=True):
        """Take a new image, and use it as the template.  NB this records the initial point.
        
        We will wait for the stage to settle, then acquire a new image to use as the template.
        Immediately afterwards, we record the first point, so we will acquire a second image
        and also read the stage's position.

        The template image will be the central 50% of the starting image, which means the 
        maximum displacement will be 0.25 fields-of-view in all directions.
        
        Arguments:
            settle: bool, default True
                Whether to wait for the stage to settle before taking the template image
            reset_history: bool, default True
                Whether to erase all the previously-stored positions
        """
        if settle:
            self.settle()
        image = self._grab_image()
        self.template = self.generate_template(image)
        self.image_shape = image.shape
        if reset_history:
            self.reset_history()
        self._template_position = np.array([0., 0.])
        self.append_point(settle=False)

    def leapfrog(self):
        """Replace the template but don't change position.

        By default, this will replace the template with the image from the last
        point we measured, but update _template_position so that the coordinates
        returned don't change.
        """
        if self._last_point is None:
            raise ValueError("Can't leapfrog until you have measured at least one point.")
        image, image_pos = self._last_point
        self.template = self.generate_template(image)
        if np.any(self.image_shape != image.shape):
            raise ValueError("Error: the image size seems to have changed!")
        # Ensure that the position doesn't change.  NB this is nice and reliable because
        # it actually runs self.track_image, but we could be much more efficient if we
        # assumed that self.track_image(image) == 0, and we can certainly do the maths
        # to make that work...
        # TODO: eliminate the unnecessary correlation
        self._template_position = np.array(image_pos)

    def generate_template(self, image):
        """Generate a template based on a supplied image.

        This function is designed to be overridden in order to
        change the tracking method.
        """
        if self.method == "direct":
            return central_half(image)
        if self.method == "fft":
            kwargs = {k: v for k, v in self.kwargs.items() if k in ["pad", "sigma"]}
            return high_pass_fft_template(image, calculate_peak=True, **kwargs)

        
    @property
    def max_displacement(self):
        """The highest position values that can be tracked"""
        if self.method == "direct":
            # TODO: if template_position is not central, should we alter this??
            disp = (np.array(self.image_shape[:2]) - np.array(self.template.shape)[:2]) // 2
        if self.method == "fft":
            # FFT tracking does a real FFT to track the position, which is half as long in
            # the last dimension.  If we didn't zero pad, the transform will have the same shape as
            # the image in x, and half in y - so we return half the image size.  If we are zero
            # padding, then both these dimensions double, and we return the image size.
            disp = np.array(self.template.shape) // np.array([2,1])
        return disp + self._template_position
    
    @property
    def min_displacement(self):
        """The lowest position values that can be tracked"""
        return self._template_position - self.max_displacement 
        # TODO: be cleverer about tracking assymetry? Currently there is none...
    
    @property
    def max_safe_displacement(self):
        """The biggest displacement we can safely attempt to track without knowing direction."""
        return np.min(np.concatenate([self.max_displacement - self._template_position, 
                                     -self.min_displacement - self._template_position]))

    def point_in_safe_range(self, point):
        """Return True if a given point is within the safe range of the tracker."""
        return np.all(point > self.min_displacement) and np.all(point < self.max_displacement)
            
    def track_image(self, image):
        """Find the position of the image relative to the template
        
        This uses the method specified at initialisation time to
        track motion of the sample.
        
        NB this class is intended to track motion of the sample - most of
        the time, we're interested in the motion of a (small) object that
        is represented by the template, relative to the (larger) image. In
        our case, we're doing the opposite - tracking motion of the image,
        relative to a picture of part of the sample.  That's why there is
        a minus sign in front of `locate_feature_in_image` in the source
        code.
        """
        if self.method=="direct":
            return -locate_feature_in_image(image, self.template, relative_to="centre") + self._template_position
        if self.method=="fft":
            kwargs = {k: v for k, v in self.kwargs.items() if k in ["pad", "fractional_threshold", "error_threshold"]}
            return -displacement_from_fft_template(self.template, image, **kwargs) + self._template_position
    
    def append_point(self, settle=True, image=None):
        """Find the current position using both stage and image, and append it"""
        if settle:
            self.settle()
        if image is None:
            image = self._grab_image()
        image_pos = self.track_image(image)
        stage_pos = self.get_position()
        self._image_positions.append(image_pos)
        self._stage_positions.append(stage_pos)
        self._last_point = (image, image_pos)
        return stage_pos, image_pos
        
    @property
    def stage_positions(self):
        """An array of positions we have moved the stage to"""
        return np.array(self._stage_positions)
    
    @property
    def image_positions(self):
        """An array of positions we have moved the stage to"""
        return np.array(self._image_positions)
    
    @property
    def history(self):
        """Return arrays of stage, image positions"""
        return TrackerHistory(self.stage_positions, self.image_positions)
    
    def reset_history(self, leave_first_point=False):
        """Reset the positions and displacements recorded"""
        if leave_first_point:
            self._stage_positions = [self._stage_positions[0]]
            self._image_positions = [self._image_positions[0]]
        else:
            self._stage_positions = []
            self._image_positions = []

    @property
    def moving_away_from_centre(self):
        """Whether we are moving away from [0,0] on the camera.

        If we have recorded more than two steps, this property will be
        `True` if the most recent point in the history is farther away from
        `[0,0]` than the second most recent point.  If we have recorded fewer
        than 2 points, this property returns None.
        """
        if len(self.image_positions) < 2:
            return None
        else:
            return norm(self.image_positions[-1,:]) > norm(self.image_positions[-2])
    
   
def move_until_motion_detected(tracker, move, displacement, threshold=10, multipliers=2**np.arange(16), detect_cumulative_motion=False):
    """Move the stage until we can detect motion in the camera.
    
    We move the stage in the direction given by ``displacement`` until the 
    image has shifted by at least ``threshold`` pixels.  The steps will be
    given by ``multipliers``, i.e. each time we move to 
    ``displacement * multipliers[i]`` relative to the starting position.
    
    NB we expect that the ``tracker`` object has already been initialised
    with ``acquire_template``.

    ``detect_cumulative_motion`` will use the first point in the tracker as
    the point to detect displacement relative to, rather than the last point.
    The displacements are always made relative to the last point in the tracker
    as it is passed in (i.e. the stage is always moved relative to where it
    currently is, but motion detection may be done relative to where the tracker
    was initialised).  This only matters if the tracker has more than one point
    in its history.

    The return value `i, m` is the number of moves made, and the largest 
    multiplier value that was used, i.e. we moved by a total of 
    `displacement * m`.
    """
    displacement = np.array(displacement)
    starting_image_position = tracker.image_positions[0 if detect_cumulative_motion else -1, :]
    starting_stage_position = tracker.stage_positions[-1, :]
    for i, m in enumerate(multipliers):
        move(starting_stage_position + displacement * m)
        tracker.append_point()
        if norm(tracker.image_positions[-1, :] - starting_image_position) >= threshold:
            return i + 1, m
    raise Exception("Moved the stage by {} but saw no motion.".format(multipliers[-1] * displacement))

def concatenate_tracker_histories(histories):
    """Combine a number of separate tracker history entries into one
    
    A "tracker history" refers to the output of `Tracker.history`, i.e.
    it is a tuple of `(stage_positions, image_positions)` with the two
    components being a Nx3 and Nx2 `numpy.ndarray` objects respectively.
    
    Given an array of such tuples, we will concatenate the components,
    returning a single "tracker history" with the segments concatenated.

    Returns: backlash, pixels_per_step, fractional_error
    
    The return value is a tuple of 3 numbers; the estimated backlash (in
    motor steps), the ratio of image_position changes to stage_position
    (in units of pixels/steps), and an estimate of goodness of fit.
    """
    components = zip(*histories)
    return tuple(np.concatenate(c, axis=1) for c in components)
