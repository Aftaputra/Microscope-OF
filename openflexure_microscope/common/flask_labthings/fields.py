# Marshmallow fields
from marshmallow.fields import *

# Marshmallow fields to JSON schema types
# Note: We shouldn't ever need to use this directly. We should go via the apispec converter
from apispec.ext.marshmallow.field_converter import DEFAULT_FIELD_MAPPING

# Extra standard library Python types
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple, Union
from uuid import UUID

# TODO: Use this to convert arbitrary dictionary into its own schema, for W3C TD
# Python types to Marshmallow fields
DEFAULT_TYPE_MAPPING = {
    bool: Boolean,
    date: Date,
    datetime: DateTime,
    Decimal: Decimal,
    float: Float,
    int: Integer,
    str: String,
    time: Time,
    timedelta: TimeDelta,
    UUID: UUID,
    dict: Dict,
    Dict: Dict,
}

# Functions to handle conversion of common Python types into serialisable Python types


def ndarray_to_list(o):
    return o.tolist()


def to_int(o):
    return int(o)


def to_float(o):
    return float(o)


def to_string(o):
    return str(o)


# Map of Python type conversions
DEFAULT_TYPE_CONVERSIONS = {
    "numpy.ndarray": ndarray_to_list,
    "numpy.int": to_int,
    "fractions.Fraction": to_float,
}

# Use with [x.__module__+"."+x.__name__ for x in inspect.getmro(type(POSSIBLE_MATCHER))]
