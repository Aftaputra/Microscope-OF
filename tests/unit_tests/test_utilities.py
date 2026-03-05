"""Unit tests for utility functions."""

import sys

import pytest

from openflexure_microscope_server.utilities import (
    _WINDOWS_RESERVED_NAMES,
    make_name_safe,
    make_path_safe,
)


def test_make_name_safe_basic():
    """Test basic functionality of make_name_safe."""
    assert make_name_safe("normal_name") == "normal_name"
    assert make_name_safe("name with spaces") == "name_with_spaces"
    assert make_name_safe("name/with/slashes") == "name_with_slashes"
    assert make_name_safe("name\\with\\backslashes") == "name_with_backslashes"


def test_make_name_safe_trailing_chars():
    """Test that trailing dots and spaces are removed."""
    assert make_name_safe("name.") == "name"
    assert make_name_safe("name ") == "name"
    assert make_name_safe("name. ") == "name"
    assert make_name_safe("name .") == "name"
    assert make_name_safe(".") == "_"
    assert make_name_safe(" ") == "_"
    assert make_name_safe(". ") == "_"


@pytest.mark.parametrize("name", _WINDOWS_RESERVED_NAMES)
def test_make_name_safe_reserved_names(name):
    """Test Windows reserved names."""
    # Base name should be sanitized
    assert make_name_safe(name) == f"{name}_"
    # Case-insensitive
    assert make_name_safe(name.lower()) == f"{name.lower()}_"
    # With extension
    assert make_name_safe(f"{name}.txt") == f"{name}.txt_"
    # Multiple extensions
    assert make_name_safe(f"{name}.tar.gz") == f"{name}.tar.gz_"


def test_make_name_safe_reserved_names_false_positives():
    """Test that names containing but not equal to reserved names are safe."""
    assert make_name_safe("CONSTANT") == "CONSTANT"
    assert make_name_safe("CON2") == "CON2"
    assert make_name_safe("ICON") == "ICON"


def test_make_path_safe_basic():
    """Test basic functionality of make_path_safe."""
    # Note: behavior depends on platform for separators
    if sys.platform.startswith("win"):
        assert make_path_safe("C:\\path\\to/file") == "C:\\path\\to/file"
    else:
        # On POSIX, \ is not a separator and might be replaced by _ if not in allowed pattern
        # The regex for POSIX is [^a-zA-Z0-9_.\-/]
        # And : is also not allowed
        assert make_path_safe("path/to/file") == "path/to/file"


def test_make_path_safe_reserved_in_components():
    """Test reserved names within path components."""
    assert make_path_safe("path/CON/file") == "path/CON_/file"
    assert make_path_safe("path/NUL.txt/file") == "path/NUL.txt_/file"

    if sys.platform.startswith("win"):
        assert make_path_safe("C:/AUX/test") == "C:/AUX_/test"
    else:
        assert make_path_safe("C:/AUX/test") == "C_/AUX_/test"


def test_make_path_safe_trailing_in_components():
    """Test trailing chars in path components."""
    assert make_path_safe("path /to. /file ") == "path/to/file"
    assert make_path_safe("path./to /file.") == "path/to/file"


def test_make_path_safe_separators():
    """Test that separators are preserved and components sanitised."""
    assert make_path_safe("a/b\\c") == "a/b\\c"
    assert make_path_safe("a./b /c.") == "a/b/c"
