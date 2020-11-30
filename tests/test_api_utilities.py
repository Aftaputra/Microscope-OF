import pytest

from openflexure_microscope.api import utilities


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("true", True),
        ("True", True),
        ("1", True),
        (True, True),
        ("false", False),
        ("somestring", False),
        (False, False),
    ],
)
def test_get_bool(test_input, expected):
    assert utilities.get_bool(test_input) == expected
