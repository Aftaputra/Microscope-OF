"""
Camera-stage calibration, 2D

Uses 2D motion to try to calibrate the relationship between a camera and a stage.


(c) Richard Bowman 2019, released under GNU GPL v3
"""
import numpy as np
import time
from numpy.linalg import norm
from matplotlib import pyplot as plt
from camera_stage_tracker import Tracker, move_until_motion_detected

from functools import partial


def backlash_corrected_move(get_position, move, backlash_amount, pos):
    """Make two moves, arriving at `pos` from a consistent direction"""
    displacement = pos - get_position()
    backlash_vector = (displacement < 0).astype(np.int) * backlash_amount
    if np.any(backlash_vector > 0):
        move(pos - backlash_vector)
    move(pos)


def bake_backlash_corrected_move(get_position, move, backlash_amount):
    """Return a function that performs backlash-corrected moves"""
    return partial(backlash_corrected_move, get_position, move, backlash_amount)


def calibrate_xy_grid(tracker, move, step=100, n_steps=4, backlash_compensation=0):
    """Make a series of moves in X and Y to determine the XY components of the pixel-to-sample matrix.

    Arguments:
    tracker: Tracker
        An initialised Tracker object, centred on the starting point.  This provides position readout from the stage and the camera.
    move: function
        A function that accepts a 1D array and performs an absolute move to 
        that position.  If backlash correction is needed, include it here.
    step : float, optional (default 100)
        The amount to move the stage by.  This should move the sample by approximately 1/10th of the field of view.
    """
    try:  # Ensure that the tracker has a template set
        _ = tracker.template
    except:
        tracker.acquire_template()
    tracker.reset_history()  # make sure we get rid of the initial (0,0) point
    starting_position = tracker.get_position()
    # Move the stage in a square, recording the displacement from both the stage and the camera
    try:
        for x in (np.arange(n_steps) - n_steps / 2.0) * step:
            for y in (np.arange(n_steps) - n_steps / 2.0) * step:
                move(starting_position + np.array([x, y, 0]))
                tracker.append_point()
    finally:
        move(starting_position)
    # We then use least-squares to fit the XY part of the matrix relating
    # pixels to distance
    # stage_positions should be the stage positions, with a zero mean.
    # image_positions should be the same, but calculated from the images
    stage_positions, image_positions = tracker.history
    stage_positions = stage_positions.astype(np.float)
    stage_positions -= np.mean(stage_positions, axis=0)
    stage_positions = stage_positions[:, :2]  # ensure it's 2d
    image_positions -= np.mean(image_positions, axis=0)
    # image_positions *= -1 # To get the matrix right, we want the position of each
    # image relative to the template, rather than the other way around
    A, res, rank, s = np.linalg.lstsq(
        image_positions, stage_positions
    )  # we solve pixel_shifts*A = location_shifts

    transformed_image_positions = np.dot(image_positions, A)
    residuals = transformed_image_positions - stage_positions
    fractional_error = norm(residuals) / stage_positions.shape[0]
    logging.debug(f"Ratio of residuals to displacement is {fractional_error})")
    if fractional_error > 0.05:  # Check it was a reasonably good fit
        logging.warning(
            "Warning: the error fitting measured displacements was %.1f%%"
            % (fractional_error * 100)
        )
    logging.info(
        f"Calibrated the pixel-location matrix.\nResiduals were {fractional_error*100:.1f}% of the shift."
    )

    return {
        "image_to_stage_displacement": A,
        "moves": (stage_positions, image_positions),
        "fractional_error": fractional_error,
    }
