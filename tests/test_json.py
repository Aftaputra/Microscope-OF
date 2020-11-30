import json
import re
import uuid
from fractions import Fraction
from uuid import uuid3

import numpy as np
import pytest

from openflexure_microscope.json import JSONEncoder


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (uuid.uuid1(), 1),
        (uuid.uuid3(uuid.NAMESPACE_DNS, "openflexure.org"), 3),
        (uuid.uuid4(), 4),
        (uuid.uuid5(uuid.NAMESPACE_DNS, "openflexure.org"), 5),
    ],
)
def test_encode_uuid(test_input, expected):
    encoded = json.dumps(test_input, cls=JSONEncoder)
    decoded = json.loads(encoded)
    assert uuid.UUID(decoded).version == expected


@pytest.mark.parametrize(
    "test_input",
    [
        Fraction(1, 2),
        Fraction(1, 3),
        Fraction(-27, 4),
        Fraction(27, -4),
        Fraction(10),
        Fraction(18, 63),
        Fraction(1, 1000000),
    ],
)
def test_encode_fraction(test_input):
    encoded = json.dumps(test_input, cls=JSONEncoder)
    decoded = json.loads(encoded)
    assert Fraction(decoded).limit_denominator() == test_input


@pytest.mark.parametrize(
    "test_input", [np.random.randint(100, dtype=np.int64) for _ in range(10)]
)
def test_encode_np_int(test_input):
    encoded = json.dumps(test_input, cls=JSONEncoder)
    decoded = json.loads(encoded)
    assert np.int64(decoded) == test_input


@pytest.mark.parametrize(
    "test_input", [np.float64(np.random.random()) for _ in range(10)]
)
def test_encode_np_float(test_input):
    encoded = json.dumps(test_input, cls=JSONEncoder)
    decoded = json.loads(encoded)
    assert np.float64(decoded) == test_input
