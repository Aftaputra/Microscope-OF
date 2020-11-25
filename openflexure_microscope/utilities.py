import base64
import copy
import logging
import time
from contextlib import contextmanager
from uuid import UUID

import numpy as np


class Timer(object):
    def __init__(self, name):
        self.name = name
        self.start = None
        self.end = None

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, type_, value, traceback):
        self.end = time.time()
        logging.debug("%s time: %s", self.name, self.end - self.start)


def deserialise_array_b64(b64_string, dtype, shape):
    flat_arr = np.frombuffer(base64.b64decode(b64_string), dtype)
    return flat_arr.reshape(shape)


def serialise_array_b64(npy_arr):
    b64_string = base64.b64encode(npy_arr).decode("ascii")
    dtype = str(npy_arr.dtype)
    shape = npy_arr.shape
    return b64_string, dtype, shape


def ndarray_to_json(arr: np.ndarray):
    if isinstance(arr, memoryview):
        # We can transparently convert memoryview objects to arrays
        # This comes in very handy for the lens shading table.
        arr = np.array(arr)
    b64_string, dtype, shape = serialise_array_b64(arr)
    return {"@type": "ndarray", "dtype": dtype, "shape": shape, "base64": b64_string}


def json_to_ndarray(json_dict: dict):
    if not json_dict.get("@type") != "ndarray":
        logging.warning("No valid @type attribute found. Conversion may fail.")
    for required_param in ("dtype", "shape", "base64"):
        if not json_dict.get(required_param):
            raise KeyError(f"Missing required key {required_param}")

    return deserialise_array_b64(
        json_dict.get("base64"), json_dict.get("dtype"), json_dict.get("shape")
    )


@contextmanager
def set_properties(obj, **kwargs):
    """A context manager to set, then reset, certain properties of an object.

    The first argument is the object, subsequent keyword arguments are properties
    of said object, which are set initially, then reset to their previous values.
    """
    saved_properties = {}
    for k in kwargs.keys():
        try:
            saved_properties[k] = getattr(obj, k)
        except AttributeError:
            print(
                "Warning: could not get {} on {}.  This property will not be restored!".format(
                    k, obj
                )
            )
    for k, v in kwargs.items():
        setattr(obj, k, v)
    try:
        yield
    finally:
        for k, v in saved_properties.items():
            setattr(obj, k, v)


def axes_to_array(
    coordinate_dictionary, axis_keys=("x", "y", "z"), base_array=None, asint=True
):
    """Takes key-value pairs of a JSON value, and maps onto an array"""
    # If no base array is given
    if not base_array:
        # Create an array of zeros
        base_array = [0] * len(axis_keys)
    else:
        # Create a copy of the passed base_array
        base_array = copy.copy(base_array)

    # Do the mapping
    for axis, key in enumerate(axis_keys):
        if key in coordinate_dictionary:
            base_array[axis] = (
                int(coordinate_dictionary[key]) if asint else coordinate_dictionary[key]
            )

    return base_array


def entry_by_uuid(entry_id: str, object_list: list):
    """Return an object from a list, if <object>.id matches id argument."""
    found = None
    if type(entry_id) == str:
        converter = str
    elif type(entry_id) == int:
        converter = int
    elif isinstance(entry_id, UUID):
        converter = int
    else:
        raise TypeError("Argument entry_id must be a string, integer, or UUID object.")
    for o in object_list:
        # Convert to strings (in case of UUID objects, for example)
        if converter(o.id) == converter(entry_id):
            found = o
    return found
