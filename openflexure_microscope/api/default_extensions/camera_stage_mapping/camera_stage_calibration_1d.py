"""
1D calibration of the relationship between a stage and a camera

The `Tracker` class in this file is used to simplify code for tasks that involve moving the
stage, and tracking the corresponding motion with the camera.

(c) Richard Bowman 2019, released under GNU GPL v3
"""
import numpy as np
import time
from numpy.linalg import norm
from .camera_stage_tracker import Tracker, move_until_motion_detected
import logging


def displacements(positions):
    """Calculate the absolute distance of each point from the first point."""
    return norm(positions - positions[0, :][np.newaxis, :], axis=1)


def direction_from_points(points):
    """Given an Nx2 array of points, figure out the principal component.
    
    The return value is a normalised vector that points along the
    direction with the most motion.
    """
    points = points.astype(np.float)
    points -= np.mean(points, axis=0)[np.newaxis, :]
    eigenvalues, eigenvectors = np.linalg.eig(np.cov(points.T))
    return eigenvectors[:, np.argmax(eigenvalues)]


def apply_backlash(x, backlash=0, start_unwound=True):
    """Apply a basic model of backlash to a set of coordinates.

    The output (y) will lag behind the input by up to `backlash`

    `start_unwound` (default: True) assumes we change direction
    at the start of the time series, so you will get no motion
    until `x[i]` has moved by at least `2*backlash`.
    """
    y = np.zeros_like(x)
    if start_unwound:
        initial_direction = np.sign(x[1] - x[0])
        y[0] = x[0] + initial_direction * backlash
    else:
        y[0] = x[0]
    for i in range(1, len(x)):
        d = x[i] - y[i - 1]
        if np.abs(d) >= backlash:
            y[i] = x[i] - np.sign(d) * backlash
        else:
            y[i] = y[i - 1]
    return y


def fit_backlash(moves):
    """Given a set of linear moves forwards and back, estimate backlash.

    The result is an estimate of the amount of backlash, and the ratio
    of steps to pixels.  The moves should be in the same
    format as `Tracker.history`.

    We use a very basic fitting method: we do a brute-force search for 
    the backlash value, and for each value of backlash we fit a line to
    the relationship between stage position (after modelling backlash) 
    and image position.  We then pick the value of backlash that gets
    the lowest residuals.  Currently the backlash values tried will
    start at 0 and increase by 1 or by a factor of 1.33 each time.

    The return value is a dictionary with the following keys:
        backlash: float
            the estimated backlash, in motor steps
        pixels_per_step: float
            the gradient of pixels to steps
        fractional_error: float
            an estimate of the goodness of fit
        stage_direction: numpy.ndarray
            unit vector in the direction of stage motion
        image_direction: numpy.ndarray
            unit vector in the direction of the motion measured
            on the camera
        pixels_per_step_vector: numpy.ndarray
            The displacement in 2D on the camera resulting from
            one step in `stage_direction`.  This is equal to the
            product of `pixels_per_step` and `image_direction`.
    """
    all_stage_points, all_image_points = moves

    # Figure out the direction of motion, and reduce everything to 1D
    image_direction = direction_from_points(all_image_points)
    stage_direction = direction_from_points(all_stage_points)
    xfit = np.sum(all_stage_points * stage_direction[np.newaxis, :], axis=1)
    yfit = np.sum(all_image_points * image_direction[np.newaxis, :], axis=1)

    # We should probably use a fancy optimiser to fit the backlash, but
    # brute-forcing it is reliable and doesn't take long.
    def fit_motion(xfit, yfit, backlash=0):
        """Using the model of backlash, fit the observed camera motion"""
        xfit_blsh = apply_backlash(xfit, backlash)
        xfit_blsh -= np.mean(xfit_blsh)
        m, c = np.polyfit(xfit_blsh, yfit, 1)
        residuals = yfit - (xfit_blsh * m + c)
        return m, c, np.std(residuals, ddof=3)

    max_backlash = (np.max(xfit) - np.min(xfit)) / 3
    backlash_values = []
    residual_values = []
    backlash = 0
    while backlash < max_backlash:
        m, c, residual = fit_motion(xfit, yfit, backlash)
        residual_values.append(residual)
        backlash_values.append(backlash)
        backlash += max(1, backlash / 3)

    backlash = backlash_values[np.argmin(residual_values)]
    m, c, residual = fit_motion(xfit, yfit, backlash)

    fractional_error = residual / norm(np.diff(yfit))
    if fractional_error > 0.1:
        raise ValueError("The fit didn't look successful")

    return {
        "backlash": backlash,
        "pixels_per_step": m,
        "fractional_error": fractional_error,
        "stage_direction": stage_direction,
        "image_direction": image_direction,
        "pixels_per_step_vector": m * image_direction,
    }


def calibrate_backlash_1d(tracker, move, direction=np.array([1, 0, 0])):
    """Figure out reasonable step sizes for calibration, and estimate the backlash."""
    try:  # Ensure that the tracker has a template set
        _ = tracker.template
    except:
        tracker.acquire_template()
    assert tracker.stage_positions.shape[0] == 1
    original_stage_pos = tracker.stage_positions[-1, :]

    direction = (
        direction / np.sum(direction ** 2) ** 0.5
    )  # ensure "direction" is normalised

    logging.info("Moving the stage until we see motion...")
    # Move the stage until we can see a significant amount of motion
    i, m = move_until_motion_detected(
        tracker, move, direction, threshold=tracker.max_safe_displacement * 0.2
    )

    logging.info("Moving the stage to the edge of the field of view...")
    i, m = move_until_motion_detected(
        tracker,
        move,
        direction,
        threshold=tracker.max_safe_displacement * 0.7,
        multipliers=m / 2.0 * np.arange(20),
        detect_cumulative_motion=True,
    )
    exponential_moves = tracker.history

    # Include this final step, and make a rough estimate of the scaling from stage to image
    stage_pos, image_pos = tracker.history
    stage_step = stage_pos[-1, :] - stage_pos[-1 - i, :]
    image_step = image_pos[-1, :] - image_pos[-1 - i, :]
    steps_per_pixel = norm(stage_step) / norm(image_step)

    # Calculate a step that moves roughly 0.2 times the max. displacement (i.e. 0.1 times the FoV)
    sensible_step = direction * tracker.max_safe_displacement * 0.2 * steps_per_pixel
    tracker.reset_history()

    logging.info("Moving the stage backwards to measure backlash (1/2)")
    # Now move backwards, in 10 steps that should roughly cross the field of view.
    # If the stage has no backlash, this will move too far, hence the break statement to
    # prevent it moving outside of the field of view.
    starting_stage_pos, starting_camera_pos = tracker.append_point()
    for i in range(15):
        move(starting_stage_pos - sensible_step * (i + 1))
        # print(".", end="")
        stage_pos, image_pos = tracker.append_point()
        if (
            i > 3
            and tracker.moving_away_from_centre
            and norm(image_pos) > 0.65 * tracker.max_safe_displacement
        ):
            break  # Stop once we have moved far enough

    logging.info("Moving the stage forwards to measure backlash (2/2)")
    # Move forwards again, in 10 steps
    starting_stage_pos, starting_camera_pos = tracker.append_point()
    for i in range(15):
        move(starting_stage_pos + sensible_step * (i + 1))
        # print(".", end="")
        stage_pos, image_pos = tracker.append_point()
        if (
            i > 3
            and tracker.moving_away_from_centre
            and norm(image_pos) > 0.65 * tracker.max_safe_displacement
        ):
            break  # Stop once we have moved far enough
    linear_moves = tracker.history

    try:
        res = fit_backlash(linear_moves)
        backlash_correction = (
            sensible_step / norm(sensible_step) * res["backlash"] * 1.5
        )

        # Finally, move back to the starting position, doing backlash-corrected moves.
        logging.info("Moving back to the start, correcting for backlash...")
        tracker.reset_history()
        stage_pos, camera_pos = tracker.append_point()
        while np.dot(stage_pos - sensible_step - original_stage_pos, sensible_step) > 0:
            move(stage_pos - sensible_step - backlash_correction)
            move(stage_pos - sensible_step)
            stage_pos, camera_pos = tracker.append_point()
        backlash_corrected_moves = tracker.history
        move(original_stage_pos - backlash_correction)
    except ValueError:
        return {"exponential_moves": exponential_moves, "linear_moves": linear_moves}
    finally:
        # Reset position
        move(original_stage_pos)

    logging.info(f"Estimated backlash {res['backlash']:.0f} steps")
    logging.info(
        f"Stage-to-image ratio {np.abs(res['pixels_per_step']):.3f} pixels/step"
    )
    logging.info(
        f"Residuals were about {res['fractional_error']:.2f} times the step size"
    )

    res.update(
        {
            "exponential_moves": exponential_moves,
            "linear_moves": linear_moves,
            "backlash_corrected_moves": backlash_corrected_moves,
        }
    )
    return res


def plot_1d_backlash_calibration(results):
    """Plot the results of a calibration run"""
    from matplotlib import pyplot as plt

    f, ax = plt.subplots(1, 2)

    for k in ["exponential", "linear", "backlash_corrected"]:
        moves = results[k + "_moves"]
        if moves is not None:
            ax[0].plot(moves[1][:, 0], moves[1][:, 1], "o-")
    ax[0].set_aspect(1, adjustable="datalim")

    image_direction = results["image_direction"]
    stage_direction = results["stage_direction"]

    def convert_moves(moves):
        stage_pos, image_pos = moves
        stage_1d = np.sum(stage_pos * stage_direction[np.newaxis, :], axis=1)
        image_1d = np.sum(image_pos * image_direction[np.newaxis, :], axis=1)
        return stage_1d, image_1d

    ax[1].plot(*convert_moves(results["exponential_moves"]), "o-")

    stage_pos, image_pos = convert_moves(results["linear_moves"])
    model = apply_backlash(stage_pos, results["backlash"])
    model *= results["pixels_per_step"]
    model += np.mean(image_pos) - np.mean(model)
    ax[1].plot(stage_pos, model, "-")
    ax[1].plot(stage_pos, image_pos, "o")
    if results["backlash_corrected_moves"] is not None:
        ax[1].plot(*convert_moves(results["backlash_corrected_moves"]), "+")

    return f, ax


def image_to_stage_displacement_from_1d(calibrations):
    """Combine X and Y calibrations

    This uses the output from `calibrate_backlash_1d`, run at least
    twice with orthogonal (or at least different) `direction` parameters.
    The resulting 2x2 transformation matrix should map from image
    to stage coordinates.  Currently, the backlash estimate given
    by this function is only really trustworthy if you've supplied
    two orthogonal calibrations - that will usually be the case.
    """
    stage_vectors = []
    image_vectors = []
    backlash = np.zeros(3)
    for cal in calibrations:
        stage_vectors.append(cal["stage_direction"][:2])
        image_vectors.append(cal["pixels_per_step_vector"])
        # our backlash estimate will be the maximum backlash
        # measured in each direction
        c_blash = np.abs(cal["backlash"] * cal["stage_direction"])
        backlash[backlash < c_blash] = c_blash[backlash < c_blash]

    A, res, rank, s = np.linalg.lstsq(
        image_vectors, stage_vectors
    )  # we solve image*A = stage
    return {
        "image_to_stage_displacement": A,
        "backlash_vector": backlash,
        "backlash": np.max(backlash),
    }
