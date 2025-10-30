"""Functions for loading, adjusting, or reading from the Picamera2 tuning file.

The functions that edit the tuning files return a new dictionary that is updated.
"""

from typing import Any
from copy import deepcopy
import os
import json

import numpy as np


THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class TuningFileError(RuntimeError):
    """Raised if the tuning file cannot be loaded for any reason."""


def load_default_tuning(sensor_model: str) -> dict:
    """Load the default tuning file for the camera.

    This will load the tuning file based on the specified sensor model.
    """
    fname = f"{sensor_model}.json"
    # Note the vc4 here. This locks us to Pi4. We will need to update this to support
    # the Raspberry Pi 5.
    tuning_path = os.path.join(THIS_DIR, "tuning_files", "vc4", fname)

    try:
        with open(tuning_path, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except (json.decoder.JSONDecodeError, IOError) as e:
        raise TuningFileError(f"Could not load tuning from {tuning_path}.") from e


def find_tuning_algo(tuning: dict[str, dict], name: str) -> dict[str, Any]:
    """Return the parameters for the named algorithm in the given camera tuning dict.

    This is the same methodolgy used in the PiCamera2 library but is provided here so
    it can be tested independently of installing picamera2

    :param tuning: The camera tuning dictionary
    :param name: The key for the algorithm in the tuning file
    :return: The algorithm from the tuning dictionary. Editing this will edit the
        original dictionary.
    """
    version = tuning.get("version", 1)
    # Version 1 of the tuning files was simply a dictionary of algorithms. Later
    # versions have an "algorithms" key, the value of which is a list of algorithms.
    if version == 1:
        return tuning[name]
    # The tuning file "algorithms" is a list of dictionaries
    algorithms = tuning["algorithms"]
    # The list is a list of dictionaries that have 1 key: the algorithm name
    algo_dict = next(algo for algo in algorithms if name in algo)
    # We want the value for that key, which is a dictionary of algorithm parameters
    return algo_dict[name]


def set_lst(
    tuning: dict,
    *,
    luminance: np.ndarray,
    cr: np.ndarray,
    cb: np.ndarray,
    colour_temp: int = 5000,
) -> dict:
    """Update the ``rpi.alsc`` section of with new lens shading tables.

    Only one set of tables is set so no adaptive lens shading will be used.

    :param tuning: The current tuning file.
    :param luminance: The table of luminance values, as (12, 16) numpy array
    :param cr: The table of cr values, as (12, 16) numpy array
    :param cb: The table of cb values, as (12, 16) numpy array
    :param colour_temp: The colour temperature to set. By default this is 5000. Set a
        different value for the PiCamera Thing to report that the lens shading is not
        calibrated.
    :return: an updated tuning dict with the new lens shading tables.
    """
    output_tuning = deepcopy(tuning)
    for table in luminance, cr, cb:
        if np.array(table).shape != (12, 16):
            raise ValueError("Lens shading tables must be 12x16!")
    alsc = find_tuning_algo(output_tuning, "rpi.alsc")
    alsc["n_iter"] = 0  # disable the adaptive part.
    alsc["luminance_strength"] = 1.0
    alsc["calibrations_Cr"] = [
        {"ct": colour_temp, "table": _as_flat_rounded_list(cr, round_to=3)}
    ]
    alsc["calibrations_Cb"] = [
        {"ct": colour_temp, "table": _as_flat_rounded_list(cb, round_to=3)}
    ]
    alsc["luminance_lut"] = _as_flat_rounded_list(luminance, round_to=3)
    return output_tuning


def lst_calibrated(tuning: dict) -> bool:
    """Whether the lens shading table is calibrated.

    This checks whether the lens shading table is has a colour temperature of 5000. As
    this is what we set on calibration. Our tuning file sets a temperature of 1234.
    """
    alsc = find_tuning_algo(tuning, "rpi.alsc")
    return alsc["calibrations_Cr"][0]["ct"] == 5000


def set_ccm(
    tuning: dict,
    col_corr_matrix: tuple[
        float, float, float, float, float, float, float, float, float
    ],
) -> dict:
    """Update the ``rpi.alsc`` section of a camera tuning dict set the colour correction matrix.

    :param tuning: The current tuning dict
    :param col_corr_matrix: The colour correction matrix to set
    :return: an updated tuning dict with the new colour correction matrix.
    """
    output_tuning = deepcopy(tuning)
    ccm = find_tuning_algo(output_tuning, "rpi.ccm")
    ccm["ccms"] = [{"ct": 5000, "ccm": col_corr_matrix}]
    return output_tuning


def get_ccm(tuning: dict) -> None:
    """Get a copy of the the ``rpi.ccm`` section of a camera tuning dict."""
    ccm = find_tuning_algo(tuning, "rpi.ccm")
    return deepcopy(ccm["ccms"])


def set_static_geq(
    tuning: dict,
    offset: int = 65535,
) -> dict:
    """Update the ``rpi.geq`` section of a camera tuning dict.

    :param tuning: the raspberry pi tuning dictionary
    :param offset: The desired green equalisation offset. Default 65535. The default is
        the maximum allowed value. This means the brightness will always be below the
        threshold where averaging is used. This is default as we always need the green
        equalisation to averages the green pixels in the red and blue rows due to the
        chief ray angle compensation issue when the the stock lens is replaced by an
        objective.
    :param return: An updated tuning dictionary
    """
    output_tuning = deepcopy(tuning)
    geq = find_tuning_algo(output_tuning, "rpi.geq")
    # max out offset to disable the adaptive green equalisation
    geq["offset"] = offset
    return output_tuning


def geq_is_static(tuning: dict) -> bool:
    """Whether the green equalisation is set to static."""
    geq = find_tuning_algo(tuning, "rpi.geq")
    return geq["offset"] == 65535


def set_ce_to_disabled(
    tuning: dict,
) -> dict:
    """Set ``ce_enable`` in ``rpi.contrast`` to zero to disable adaptive contrast enhancement.

    :param tuning: The raspberry pi camera tuning file.
    :returns: A deepcopy of the input file with ce_enable set to 0.
    """
    output_tuning = deepcopy(tuning)
    contrast = find_tuning_algo(output_tuning, "rpi.contrast")
    contrast["ce_enable"] = 0
    return output_tuning


def ce_enable_is_static(tuning: dict) -> bool:
    """Whether the ce_enable flag is disabled."""
    contrast = find_tuning_algo(tuning, "rpi.contrast")
    return contrast["ce_enable"] == 0


def copy_algo_from_other_tuning(
    algo: str, *, base_tuning_file: dict, copy_from: dict
) -> dict:
    """Return a copy of tuning_file with an algorithm copied from another file.

    Tuning dict arguments are keyword only for clarity.

    :param algo: The algorithm to copy. Eg ``rpi.alsc`` for lens shading correction.
    :param base_tuning_file: The tuning file to copy.
    :param copy_alsc_from: The tuning file to take the alsc section from.
    :return: A deep copy of base_tuning_file with the alsc section copied in from the
        other tuning file.
    """
    output_tuning = deepcopy(base_tuning_file)
    # Find the relevant sub-dict for each tuning file
    from_i = _index_of_algorithm(copy_from["algorithms"], algo)
    to_i = _index_of_algorithm(base_tuning_file["algorithms"], algo)
    # Updating the output_tuning copy.
    output_tuning["algorithms"][to_i] = deepcopy(copy_from["algorithms"][from_i])
    return output_tuning


def _index_of_algorithm(algorithms: list[dict], algorithm: str) -> int:
    """Find the index of an algorithm's section in the tuning file."""
    for i, a in enumerate(algorithms):
        if algorithm in a:
            return i
    raise ValueError(f"Algorithm {algorithm} is not available.")


def _as_flat_rounded_list(array: np.ndarray, round_to: int = 3) -> list[float]:
    """Flatten array, round, and then convert to list."""
    return np.reshape(array, -1).round(round_to).tolist()
