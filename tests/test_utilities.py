import numpy as np

from openflexure_microscope import utilities


def test_serialise_array_b64():
    shape_in = (3, 2)
    arr_in = np.random.randint(100, size=shape_in, dtype=np.int)

    b64_string, dtype, shape = utilities.serialise_array_b64(arr_in)
    assert b64_string
    assert dtype == "int32"
    assert shape == shape_in

    arr_out = utilities.deserialise_array_b64(b64_string, dtype, shape)
    assert np.array_equal(arr_out, arr_in)


def test_ndarray_to_json():
    shape_in = (3, 2)
    arr_in = np.random.randint(100, size=shape_in, dtype=np.int)

    json_out = utilities.ndarray_to_json(arr_in)

    arr_out = utilities.json_to_ndarray(json_out)
    assert np.array_equal(arr_out, arr_in)


def test_axes_to_array():
    dict_in = {"x": 1, "y": 2, "z": 3}
    assert utilities.axes_to_array(dict_in) == [1, 2, 3]
