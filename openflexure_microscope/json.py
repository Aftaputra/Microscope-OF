from fractions import Fraction
from uuid import UUID

import numpy as np
from labthings.json import LabThingsJSONEncoder

__all__ = ["JSONEncoder", "LabThingsJSONEncoder"]


class JSONEncoder(LabThingsJSONEncoder):
    """
    A custom JSON encoder, with type conversions for PiCamera fractions, Numpy integers, and Numpy arrays
    """

    def default(self, o):
        if isinstance(o, UUID):
            return str(o)
        # PiCamera fractions
        elif isinstance(o, Fraction):
            return float(o)
        # Numpy integers
        elif isinstance(o, np.integer):
            return int(o)
        # Numpy floats are just Python floats
        elif isinstance(o, float):
            return float(o)
        # Numpy arrays
        elif isinstance(o, np.ndarray):
            return o.tolist()
        else:
            # call base class implementation which takes care of
            # raising exceptions for unsupported types
            return LabThingsJSONEncoder.default(self, o)
