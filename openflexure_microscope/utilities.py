import copy
import operator
from functools import reduce

def axes_to_array(coordinate_dictionary, axis_keys=['x', 'y', 'z'], base_array=None):
    """Takes key-value pairs of a JSON value, and maps onto an array"""
    # If no base array is given
    if not base_array:
        # Create an array of zeros
        base_array = [0]*len(axis_keys)
    else:
        # Create a copy of the passed base_array
        base_array = copy.copy(base_array)

    # Do the mapping
    for axis, key in enumerate(axis_keys):
        if key in coordinate_dictionary:
            base_array[axis] = coordinate_dictionary[key]

    return base_array

def filter_dict(dictionary: dict, keys: list):
	# Get value by recursively applying getitem
	val = reduce(operator.getitem, keys, dictionary)
	
	# Create new dictionary by running reduce on key, val pairs
	out = reduce(lambda x, y: {y: x}, reversed(keys), val)
	
	return out