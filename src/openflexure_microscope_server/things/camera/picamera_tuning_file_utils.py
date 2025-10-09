"""Functions for loading, adjusting, or reading from the Picamera2 tuning file.

The functions that edit the tuning files edit them in place. This will change in
the future.
"""

from picamera2 import Picamera2
import numpy as np


def load_default_tuning(sensor_model: str) -> dict:
    """Load the default tuning file for the camera.

    This will loat the tuning file based on the specified sensor model.
    """
    fname = f"{sensor_model}.json"
    try:
        return Picamera2.load_tuning_file(fname)
    except RuntimeError:
        tuning_dir = "/usr/share/libcamera/ipa/raspberrypi"
        # from picamera2 v0.3.9
        # The directory above has been removed from the search path seems
        # odd - as that's where the files currently are on a default
        # Raspbian image. This may need updating if the files have moved
        # in future updates to the system libcamera package
        return Picamera2.load_tuning_file(fname, dir=tuning_dir)


def set_static_lst(
    tuning: dict,
    luminance: np.ndarray,
    cr: np.ndarray,
    cb: np.ndarray,
) -> None:
    """Update the ``rpi.alsc`` section of a camera tuning dict to use a static correction.

    ``tuning`` will be updated in-place to set its shading to static, and disable any
    adaptive tweaking by the algorithm.
    """
    for table in luminance, cr, cb:
        if np.array(table).shape != (12, 16):
            raise ValueError("Lens shading tables must be 12x16!")
    alsc = Picamera2.find_tuning_algo(tuning, "rpi.alsc")
    alsc["n_iter"] = 0  # disable the adaptive part
    alsc["luminance_strength"] = 1.0
    alsc["calibrations_Cr"] = [
        {"ct": 4500, "table": _as_flat_rounded_list(cr, round_to=3)}
    ]
    alsc["calibrations_Cb"] = [
        {"ct": 4500, "table": _as_flat_rounded_list(cb, round_to=3)}
    ]
    alsc["luminance_lut"] = _as_flat_rounded_list(luminance, round_to=3)


def set_static_ccm(
    tuning: dict,
    col_corr_matrix: tuple[
        float, float, float, float, float, float, float, float, float
    ],
) -> None:
    """Update the ``rpi.alsc`` section of a camera tuning dict to use a static correction.

    ``tuning`` will be updated in-place to set its shading to static, and disable any
    adaptive tweaking by the algorithm.
    """
    ccm = Picamera2.find_tuning_algo(tuning, "rpi.ccm")
    ccm["ccms"] = [{"ct": 2860, "ccm": col_corr_matrix}]


def get_static_ccm(tuning: dict) -> None:
    """Get the ``rpi.ccm`` section of a camera tuning dict."""
    ccm = Picamera2.find_tuning_algo(tuning, "rpi.ccm")
    return ccm["ccms"]


def lst_is_static(tuning: dict) -> bool:
    """Whether the lens shading table is set to static."""
    alsc = Picamera2.find_tuning_algo(tuning, "rpi.alsc")
    return alsc["n_iter"] == 0


def set_static_geq(
    tuning: dict,
    offset: int = 65535,
) -> None:
    """Update the ``rpi.geq`` section of a camera tuning dict.

    :param tuning: the raspberry pi tuning file. This will be updated in-place to
        set the geq offset to the given value.
    :param offset: The desired green equalisation offset. Default 65535. The default is
        the maximum allowed value. This means the brightness will always be below the
        threshold where averaging is used. This is default as we always need the green
        equalisation to averages the green pixels in the red and blue rows due to the
        chief ray angle compensation issue when the the stock lens is replaced by an
        objective.
    """
    geq = Picamera2.find_tuning_algo(tuning, "rpi.geq")
    geq["offset"] = offset  # max out offset to disable the adaptive green equalisation


def geq_is_static(tuning: dict) -> bool:
    """Whether the green equalisation is set to static."""
    geq = Picamera2.find_tuning_algo(tuning, "rpi.geq")
    return geq["offset"] == 65535


def set_ce_to_disabled(
    tuning: dict,
) -> None:
    """Update the ``rpi.ce_enable`` section of a camera tuning dict.

    :param tuning: the raspberry pi tuning file. This will be updated in-place to
        set ce_enable to 0.
    """
    contrast = Picamera2.find_tuning_algo(tuning, "rpi.contrast")
    contrast["ce_enable"] = (
        0  # disable ce_enable to prevent adaptive contrast enhancement
    )


def ce_enable_is_static(tuning: dict) -> bool:
    """Whether the ce_enable flag is disabled."""
    contrast = Picamera2.find_tuning_algo(tuning, "rpi.contrast")
    return contrast["ce_enable"] == 0


def copy_alsc_section(from_tuning: dict, to_tuning: dict) -> None:
    """Copy the ``rpi.alsc`` algorithm from one tuning to another.

    This is done in-place, i.e. modifying to_tuning.
    """
    # Using Picamera2 function to find the relevant sub-dict for each tuning file
    from_i = _index_of_algorithm(from_tuning["algorithms"], "rpi.alsc")
    to_i = _index_of_algorithm(to_tuning["algorithms"], "rpi.alsc")
    # Updating the dictionary in place.
    to_tuning["algorithms"][to_i] = from_tuning["algorithms"][from_i]


def _index_of_algorithm(algorithms: list[dict], algorithm: str) -> int:
    """Find the index of an algorithm's section in the tuning file."""
    for i, a in enumerate(algorithms):
        if algorithm in a:
            return i
    raise ValueError(f"Algorithm {algorithm} is not available.")


def _as_flat_rounded_list(array: np.ndarray, round_to: int = 3) -> list[float]:
    """Flatten array, round, and then convert to list."""
    return np.reshape(array, -1).round(round_to).tolist()
