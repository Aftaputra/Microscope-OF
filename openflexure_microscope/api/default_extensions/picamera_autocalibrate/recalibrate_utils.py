import logging
import time
from fractions import Fraction
from typing import List, Optional, Tuple

import numpy as np
from picamerax import PiCamera
from picamerax.array import PiBayerArray, PiRGBArray

# I have used f strings throughout, for readability.
# The performance implication of using them in logging statements
# really doesn't matter here - also, loglevel is usually set to
# INFO to report progress via the LabThings action API
# pylint: disable=logging-fstring-interpolation


def rgb_image(
    camera: PiCamera, resize: Optional[Tuple[int, int]] = None, **kwargs
) -> PiRGBArray:
    """Capture an image and return an RGB numpy array"""
    with PiRGBArray(camera, size=resize) as output:
        camera.capture(output, format="rgb", resize=resize, **kwargs)
        return output.array


def flat_lens_shading_table(camera: PiCamera) -> np.ndarray:
    """Return a flat (i.e. unity gain) lens shading table.
    
    This is mostly useful because it makes it easy to get the size
    of the array correct.  NB if you are not using the forked picamera
    library (with lens shading table support) it will raise an error.
    """
    if not hasattr(PiCamera, "lens_shading_table"):
        raise ImportError(
            "This program requires the forked picamera library with lens shading support"
        )
    # pylint: disable=protected-access
    return np.zeros(camera._lens_shading_table_shape(), dtype=np.uint8) + 32


def adjust_exposure_to_setpoint(camera: PiCamera, setpoint: int):
    """Adjust the camera's exposure time until the maximum pixel value is <setpoint>."""
    print("Adjusting shutter speed to hit setpoint {}".format(setpoint), end="")
    for _ in range(3):
        print(".", end="")
        camera.shutter_speed = int(
            camera.shutter_speed * setpoint / np.max(rgb_image(camera))
        )
        time.sleep(1)
    print("done")


def adjust_exposure_and_gain(
    camera: PiCamera, target_white_level: int = 700, max_iterations: int = 99
):
    """Adjust exposure and analog gain based on raw images.
    
    This routine is slow but effective.  It uses raw images, so we
    are not affected by white balance or digital gain.
    """
    # Start by setting fully manual exposure.
    camera.exposure_mode = "off"
    camera.iso = 0  # We must set ISO=0 (auto) or we can't set gain
    camera.analog_gain = 1
    camera.digital_gain = 1
    camera.shutter_speed = 1  # This is not valid - we'll get the minimum
    time.sleep(0.5)

    # We start with very low exposure settings and work up in coarse steps
    # until either the brightness is high enough, or we can't increase the
    # shutter speed any more.
    iterations = 0
    while True:
        iterations += 1
        if iterations > max_iterations:
            logging.warning(
                f"Auto exposure is stopping after {max_iterations} "
                "but it has not converged."
            )
            break

        with PiBayerArray(camera) as a:
            camera.capture(a, format="jpeg", bayer=True)
            max_brightness = np.max(a.array)

        if max_brightness > target_white_level:
            break

        previous_shutter_speed = camera.shutter_speed
        camera.shutter_speed = previous_shutter_speed * 2
        time.sleep(0.5)
        current_shutter_speed = camera.shutter_speed
        # NB we save this in a variable in case it changes between
        # here and the next loop
        logging.info(
            f"Max brightness {max_brightness} < {target_white_level}. "
            f"Attempting to double exposure from "
            f"{previous_shutter_speed} to {current_shutter_speed}"
        )
        if current_shutter_speed == previous_shutter_speed:
            logging.info("Shutter speed has saturated, stopping.")
            break

    if max_brightness > target_white_level:
        logging.info("Brightness is high enough, fine-tuning")
        camera.shutter_speed = int(
            current_shutter_speed * target_white_level / max_brightness
        )


def auto_expose_and_freeze_settings(camera: PiCamera):
    """Freeze the settings after auto-exposing to white illumination"""
    logging.info("Allowing the camera to auto-expose")
    if "greyworld" in camera.AWB_MODES:
        logging.info("Calibrating with greyworld AWB")
        camera.awb_mode = "greyworld"
    else:
        logging.warning("Calibrating with auto AWB as greyworld is missing")
        camera.awb_mode = "auto"
    camera.exposure_mode = "auto"
    camera.iso = (
        0  # This is important, if it's on a fixed ISO, gain might not set properly.
    )
    for _ in range(6):
        print(".", end="")
        time.sleep(0.5)
    logging.info("done")

    logging.info("Freezing the camera settings...")
    camera.shutter_speed = camera.exposure_speed
    logging.info("Shutter speed = %s", (camera.shutter_speed))
    camera.exposure_mode = "off"
    logging.info("Auto exposure disabled")
    g: Tuple[Fraction, Fraction] = camera.awb_gains
    camera.awb_mode = "off"
    camera.awb_gains = g
    logging.info("Auto white balance disabled, gains are %s", (g))
    logging.info(
        "Analogue gain: %s, Digital gain: %s", camera.analog_gain, camera.digital_gain
    )
    adjust_exposure_to_setpoint(camera, 215)


def adjust_shutter_and_gain_from_raw(
    camera: PiCamera,
    target_white_level: int = 700,
    max_iterations: int = 20,
    tolerance: float = 0.05,
    percentile: float = 99.9,
) -> float:
    """Adjust exposure and analog gain based on raw images.
    
    This routine is slow but effective.  It uses raw images, so we
    are not affected by white balance or digital gain.
    """
    # Start by setting fully manual exposure.
    camera.exposure_mode = "off"
    camera.iso = 0  # We must set ISO=0 (auto) or we can't set gain
    camera.analog_gain = 1
    camera.digital_gain = 1
    camera.shutter_speed = 1  # This is not valid - we'll get the minimum
    time.sleep(0.5)

    # We start with very low exposure settings and work up in coarse steps
    # until either the brightness is high enough, or we can't increase the
    # shutter speed any more.
    iterations = 0
    shutter_speed_increments = [10, 2, None]
    shutter_speed_increment = shutter_speed_increments.pop(0)
    while iterations < max_iterations:
        iterations += 1
        max_brightness = np.max(get_channel_percentiles(camera, percentile))
        tested_shutter_speed = camera.shutter_speed
        tested_analog_gain = camera.analog_gain
        logging.info(
            f"Brightness: {max_brightness: >5.0f}, "
            f"Target: {target_white_level: >5.0f}, "
            f"Gain: {float(tested_analog_gain): >4.1f}, "
            f"Shutter: {float(tested_shutter_speed): >7.0f}"
        )

        if abs(max_brightness - target_white_level) < target_white_level * tolerance:
            logging.info(
                f"Brightness has converged to within {tolerance * 100 :.0f}% "
                f"after {iterations} iterations."
            )
            break

        # if not shutter_speed_maximised:  # Start by adjusting shutter speed
        if max_brightness > target_white_level // 2:
            shutter_speed_increment = (
                None
            )  # If we're within a factor of 2, trigger fine-tuning
        if shutter_speed_increment is None:
            logging.info("Fine-tuning shutter speed")
            new_shutter_speed = int(
                tested_shutter_speed * target_white_level / max_brightness
            )
            camera.shutter_speed = new_shutter_speed
        else:
            if max_brightness > target_white_level:
                logging.info("Reducing shutter speed")
                camera.shutter_speed = int(
                    tested_shutter_speed / shutter_speed_increment
                )
            else:
                logging.info("Increasing shutter speed")
                camera.shutter_speed = tested_shutter_speed * shutter_speed_increment
        time.sleep(0.5)

        # Check whether the shutter speed is still going up - if not, we've hit a maximum
        current_shutter_speed = camera.shutter_speed
        if current_shutter_speed == tested_shutter_speed:
            camera.analog_gain *= 2
            if camera.analog_gain == tested_analog_gain:
                logging.info("Shutter speed and gain are both maxed out.  Giving up!")
                break
            logging.info("Shutter speed has maxed out, doubled gain to compensate.")
    return max_brightness


def adjust_white_balance_from_raw(
    camera: PiCamera, percentile: float = 99
) -> Tuple[float, float]:
    """Adjust the white balance in a single shot, based on the raw image.
    
    NB if ``channels_from_raw_image`` is broken, this will go haywire.
    We should probably have better logic to verify the channels really
    are BGGR...
    """
    blue, g1, g2, red = get_channel_percentiles(camera, percentile)
    green = (g1 + g2) / 2.0
    new_awb_gains = (green / red, green / blue)
    logging.info(
        f"Raw white point is R: {red} G: {green} B: {blue}, "
        f"setting AWB gains to ({new_awb_gains[0]:.2f}, "
        f"{new_awb_gains[1]:.2f})."
    )
    camera.awb_mode = "off"
    camera.awb_gains = new_awb_gains
    return new_awb_gains


def channels_from_bayer_array(bayer_array: np.ndarray) -> np.ndarray:
    """Given the 'array' from a PiBayerArray, return the 4 channels."""
    bayer_pattern: List[Tuple[int, int]] = [(0, 0), (0, 1), (1, 0), (1, 1)]
    channels_shape: Tuple[int, ...] = (
        4,
        bayer_array.shape[0] // 2,
        bayer_array.shape[1] // 2,
    )
    channels: np.ndarray = np.zeros(channels_shape, dtype=bayer_array.dtype)
    for i, offset in enumerate(bayer_pattern):
        # We simplify life by dealing with only one channel at a time.
        channels[i, :, :] = np.sum(
            bayer_array[offset[0] :: 2, offset[1] :: 2, :], axis=2
        )

    return channels


def get_channel_percentiles(camera: PiCamera, percentile: float) -> np.ndarray:
    """Calculate the brightness percentile of the pixels in each channel"""
    with PiBayerArray(camera) as output:
        camera.capture(output, format="jpeg", bayer=True)
        channels = channels_from_bayer_array(output.array)
        return np.percentile(channels, percentile, axis=(1, 2))


def lst_from_channels(channels: np.ndarray) -> np.ndarray:
    """Given the 4 Bayer colour channels from a white image, generate a LST."""
    full_resolution: np.ndarray = np.array(
        channels.shape[1:]
    ) * 2  # channels have been binned

    # NOTE: the size of the LST is 1/64th of the image, but rounded UP.
    lst_resolution: List[int] = [(r // 64) + 1 for r in full_resolution]

    logging.info("Generating a lens shading table at %sx%s", *lst_resolution)
    lens_shading: np.ndarray = np.zeros(
        [channels.shape[0]] + lst_resolution, dtype=np.float
    )
    for i in range(lens_shading.shape[0]):
        image_channel: np.ndarray = channels[i, :, :]
        iw: int
        ih: int
        iw, ih = image_channel.shape
        ls_channel: np.ndarray = lens_shading[i, :, :]
        lw: int
        lh: int
        lw, lh = ls_channel.shape
        # The lens shading table is rounded **up** in size to 1/64th of the size of
        # the image.  Rather than handle edge images separately, I'm just going to
        # pad the image by copying edge pixels, so that it is exactly 32 times the
        # size of the lens shading table (NB 32 not 64 because each channel is only
        # half the size of the full image - remember the Bayer pattern...  This
        # should give results very close to 6by9's solution, albeit considerably
        # less computationally efficient!
        padded_image_channel: np.ndarray = np.pad(
            image_channel, [(0, lw * 32 - iw), (0, lh * 32 - ih)], mode="edge"
        )  # Pad image to the right and bottom
        logging.info(
            "Channel shape: %sx%s, shading table shape: %sx%s, after padding %s",
            iw,
            ih,
            lw * 32,
            lh * 32,
            padded_image_channel.shape,
        )
        # Next, fill the shading table (except edge pixels).  Please excuse the
        # for loop - I know it's not fast but this code needn't be!
        box: int = 3  # We average together a square of this side length for each pixel.
        # NB this isn't quite what 6by9's program does - it averages 3 pixels
        # horizontally, but not vertically.
        for dx in np.arange(box) - box // 2:
            for dy in np.arange(box) - box // 2:
                ls_channel[:, :] += (
                    padded_image_channel[16 + dx :: 32, 16 + dy :: 32] - 64
                )
        ls_channel /= box ** 2
        # The original C code written by 6by9 normalises to the central 64 pixels in each channel.
        # ls_channel /= np.mean(image_channel[iw//2-4:iw//2+4, ih//2-4:ih//2+4])
        # I have had better results just normalising to the maximum:
        ls_channel /= np.max(ls_channel)
        # NB the central pixel should now be *approximately* 1.0 (may not be exactly
        # due to different averaging widths between the normalisation & shading table)
        # For most sensible lenses I'd expect that 1.0 is the maximum value.
        # NB ls_channel should be a "view" of the whole lens shading array, so we don't
        # need to update the big array here.

    # What we actually want to calculate is the gains needed to compensate for the
    # lens shading - that's 1/lens_shading_table_float as we currently have it.
    gains: np.ndarray = 32.0 / lens_shading  # 32 is unity gain
    gains[gains > 255] = 255  # clip at 255, maximum gain is 255/32
    gains[gains < 32] = 32  # clip at 32, minimum gain is 1 (is this necessary?)
    lens_shading_table: np.ndarray = gains.astype(np.uint8)
    return lens_shading_table[::-1, :, :].copy()


def lst_from_camera(camera: PiCamera) -> np.ndarray:
    """Acquire a raw image and use it to calculate a lens shading table."""
    with PiBayerArray(camera) as a:
        camera.capture(a, format="jpeg", bayer=True)
        raw_image = a.array.copy()

    # Now we need to calculate a lens shading table that would make this flat.
    # raw_image is a 3D array, with full resolution and 3 colour channels.  No
    # de-mosaicing has been done, so 2/3 of the values are zero (3/4 for R and B
    # channels, 1/2 for green because there's twice as many green pixels).
    channels = channels_from_bayer_array(raw_image)
    return lst_from_channels(channels)


def recalibrate_camera(camera: PiCamera):
    """Reset the lens shading table and exposure settings.

    This method first resets to a flat lens shading table, then auto-exposes,
    then generates a new lens shading table to make the current view uniform.
    It should be run when the camera is looking at a uniform white scene.

    NB the only parameter ``camera`` is a ``PiCamera`` instance and **not** a
    ``StreamingCamera``.
    """
    camera.lens_shading_table = flat_lens_shading_table(camera)
    _ = rgb_image(camera)  # for some reason the camera won't work unless I do this!

    lens_shading_table = lst_from_camera(camera)

    camera.lens_shading_table = lens_shading_table
    _ = rgb_image(camera)

    # Fix the AWB gains so the image is neutral
    channel_means = np.mean(np.mean(rgb_image(camera), axis=0, dtype=np.float), axis=0)
    old_gains = camera.awb_gains
    camera.awb_gains = (
        channel_means[1] / channel_means[0] * old_gains[0],
        channel_means[1] / channel_means[2] * old_gains[1],
    )
    time.sleep(1)
    # Ensure the background is bright but not saturated
    adjust_exposure_to_setpoint(camera, 230)


if __name__ == "__main__":
    with PiCamera() as main_camera:
        main_camera.start_preview()
        time.sleep(3)
        logging.info("Recalibrating...")
        recalibrate_camera(main_camera)
        logging.info("Done.")
        time.sleep(2)
