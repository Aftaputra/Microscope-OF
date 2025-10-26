"""Test the utilities functions."""

import pytest

from openflexure_microscope_server import utilities


@pytest.mark.parametrize(
    ("target", "patch", "outcome", "err_if_enforce"),
    [
        ({"a": "b"}, {"a": "c"}, {"a": "c"}, False),
        ({"a": "b"}, {"b": "c"}, {"a": "b", "b": "c"}, False),
        ({"a": "b"}, {"a": None}, {}, False),
        ({"a": "b", "b": "c"}, {"a": None}, {"b": "c"}, False),
        ({"a": ["b"]}, {"a": "c"}, {"a": "c"}, False),
        ({"a": "c"}, {"a": ["b"]}, {"a": ["b"]}, False),
        (
            {"a": {"b": "c"}},
            {"a": {"b": "d", "c": None}},
            {"a": {"b": "d"}},
            False,
        ),
        ({"a": [{"b": "c"}]}, {"a": [1]}, {"a": [1]}, False),
        (["a", "b"], ["c", "d"], ["c", "d"], True),
        ({"a": "b"}, ["c"], ["c"], True),
        ({"a": "foo"}, None, None, True),
        ({"a": "foo"}, "bar", "bar", True),
        ({"e": None}, {"a": 1}, {"e": None, "a": 1}, False),
        ([1, 2], {"a": "b", "c": None}, {"a": "b"}, True),
        ({}, {"a": {"bb": {"ccc": None}}}, {"a": {"bb": {}}}, False),
    ],
)
def test_merge_patch(target, patch, outcome, err_if_enforce):
    """Check that merge_patch returns the expected outcome for each target and patch.

    These test cases are specified in Appedix A of IETF RFC 7396.
    """
    assert utilities.merge_patch(target, patch) == outcome

    # If expected to error when enforce_dict is True then check:
    if err_if_enforce:
        with pytest.raises(ValueError, match="Both target and patch"):
            utilities.merge_patch(target, patch, enforce_dict=True)
    else:
        # Else should run without error with same expected value
        assert utilities.merge_patch(target, patch, enforce_dict=True) == outcome
