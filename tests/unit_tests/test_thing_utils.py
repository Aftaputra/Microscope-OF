"""Test selector coercion logic for Thing mappings."""

import logging

import pytest

from openflexure_microscope_server.utilities import coerce_thing_selector


@pytest.mark.parametrize(
    ("selected", "default", "warning_count"),
    [
        ("a", "b", 1),
        (None, "b", 0),
        ("a", None, 1),
        (None, None, 0),
    ],
)
def test_coerce_with_empty_mapping(selected, default, warning_count, caplog):
    """Test None always returned for empty mappings, check warnings when appropriate."""
    with caplog.at_level(logging.WARNING):
        output = coerce_thing_selector(
            thing_mapping={}, selected=selected, default=default
        )
    assert output is None
    assert len(caplog.records) == warning_count


@pytest.mark.parametrize(
    ("selected", "default", "returned", "warning_count"),
    [
        ("b", "b", "b", 0),
        ("b", "a", "b", 0),
        ("b", None, "b", 0),
        ("b", "z", "b", 0),
        (None, "b", "b", 0),
        (None, "a", "a", 0),
        (None, None, "a", 0),
        (None, "z", "a", 1),
        ("z", "b", "b", 1),
        ("z", "a", "a", 1),
        ("z", None, "a", 1),
        ("z", "z", "a", 2),
    ],
)
def test_coerce_with_populated_mapping(
    selected, default, returned, warning_count, caplog
):
    """Test coercion of selected key for a populated thing mapping.

    Check that warnings are raised when appropriate.
    """
    thing_mapping = {"a": "Foo", "b": "Bar", "c": "FooBar"}
    with caplog.at_level(logging.WARNING):
        output = coerce_thing_selector(
            thing_mapping=thing_mapping, selected=selected, default=default
        )
    assert output == returned
    assert len(caplog.records) == warning_count
