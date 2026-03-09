"""Unit tests for utility functions."""

import logging
import sys

import pytest

from openflexure_microscope_server.utilities import (
    _WINDOWS_RESERVED_NAMES,
    make_name_safe,
    make_path_safe,
)

PATHS_WITH_DOTS = {"a./b/c.", "path./to/file.", "./path./to/file."}

RESERVED_NAME_PATHS = {"path/CON/file", "path/NUL.txt/file", "C:/AUX/test"}

if sys.platform.startswith("win"):
    UNSAFE_CHARACTER_PATHS = {
        "C:/path/asterisk/data*.csv",
        "data/files/read_me_first!.txt",
        "logs/system<error>.log",
        "projects/alpha#1/notes.txt",
    }
else:
    UNSAFE_CHARACTER_PATHS = {
        "/var/log/app:backup.log",
        "/etc/configs/network-settings\\v1",
        "/tmp/file_with_@_symbol.txt",
        "/home/user/script(1).py",
    }


def test_make_name_safe_basic():
    """Test basic functionality of make_name_safe."""
    assert make_name_safe("normal_name") == "normal_name"
    assert make_name_safe("name with spaces") == "name_with_spaces"
    assert make_name_safe("name/with/slashes") == "name_with_slashes"
    assert make_name_safe("name\\with\\backslashes") == "name_with_backslashes"
    assert make_name_safe("sPoNgEmoCk") == "spongemock"


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
    assert make_name_safe(name) == f"{name.lower()}_"
    # Case-insensitive
    assert make_name_safe(name.lower()) == f"{name.lower()}_"
    # With extension
    assert make_name_safe(f"{name}.txt") == f"{name.lower()}.txt_"
    # Multiple extensions
    assert make_name_safe(f"{name}.tar.gz") == f"{name.lower()}.tar.gz_"


def test_make_name_safe_reserved_names_false_positives():
    """Test that names containing but not equal to reserved names are safe."""
    assert make_name_safe("CONSTANT") == "constant"
    assert make_name_safe("CON2") == "con2"
    assert make_name_safe("ICON") == "icon"
    assert make_name_safe("icon") == "icon"
    assert make_name_safe("iCon") == "icon"
    assert make_name_safe("iCOn") == "icon"
    assert make_name_safe("icOn") == "icon"
    assert make_name_safe("CHILLI CON CARNE") == "chilli_con_carne"


def test_make_path_safe_basic(caplog):
    """Test basic functionality of make_path_safe."""
    # Note: behavior depends on platform for separators
    with caplog.at_level(logging.WARNING):
        if sys.platform.startswith("win"):
            assert make_path_safe("C:\\path\\to/file")[0] == "C:\\path\\to/file"
            assert (
                make_path_safe("C:\\a very long path\\to/file")[0]
                == "C:\\a very long path\\to/file"
            )
        else:
            assert make_path_safe("path/to/file")[0] == "path/to/file"
            assert (
                make_path_safe("a very long path/to/file")[0]
                == "a very long path/to/file"
            )

        # No errors should be raised. These paths are safe.
        assert len(caplog.records) == 0


@pytest.mark.parametrize("path", UNSAFE_CHARACTER_PATHS)
def test_make_path_safe_unsafe_characters_in_components(caplog, path):
    """Test unsafe characters within path components."""
    with caplog.at_level(logging.WARNING):
        assert make_path_safe(path)[0] == path
        assert (
            f"{path} contains characters that may be unsafe on this platform."
            in caplog.messages
        )


@pytest.mark.parametrize("path", RESERVED_NAME_PATHS)
def test_make_path_safe_reserved_in_components(caplog, path):
    """Test reserved names within path components."""
    with caplog.at_level(logging.WARNING):
        assert make_path_safe(path)[0] == path
        assert (
            f"{path} contains a reserved system name and may cause issues."
            in caplog.messages
        )


def test_make_path_safe_trailing_space_in_components(caplog):
    """Test trailing spaces in path components."""
    with caplog.at_level(logging.WARNING):
        # Test Windows - cannot have trailingspaces
        if sys.platform.startswith("win"):
            assert make_path_safe("path /to /file ")[0] == "path /to /file "
            assert make_path_safe("path/to /file")[0] == "path/to /file"
            # Check directories can have spaces in them but not at the end
            assert (
                make_path_safe("path/a long path name /file")[0]
                == "path/a long path name /file"
            )
            assert len(caplog.records) == 3
            assert "path /to /file  contains unsafe trailing spaces." in caplog.messages
            assert "path/to /file contains unsafe trailing spaces." in caplog.messages
            assert (
                "path/a long path name /file contains unsafe trailing spaces."
                in caplog.messages
            )
        else:
            # Trailing spaces allows in POSIX systems
            assert make_path_safe("path /to /file ")[0] == "path /to /file "
            assert make_path_safe("path/to /file")[0] == "path/to /file"
            # Check directories can have spaces in them but not at the end
            assert (
                make_path_safe("path/a long path name  /file")[0]
                == "path/a long path name file"
            )
            # No warnings should be raised
            assert len(caplog.records) == 0


def test_make_path_safe_relative(caplog):
    """Test that relative path components are preserved."""
    # Relative imports ./foo, ../foo or ../../foo are allowed.
    with caplog.at_level(logging.WARNING):
        assert make_path_safe("./openflexure/data/")[0] == "./openflexure/data/"
        assert make_path_safe("../openflexure/data/")[0] == "../openflexure/data/"
        assert make_path_safe("../../openflexure/data/")[0] == "../../openflexure/data/"
        assert make_path_safe(".")[0] == "."
        assert make_path_safe("..")[0] == ".."

        assert len(caplog.records) == 0

        assert make_path_safe("a_bad/../relative_path")[0] == "a_bad/../relative_path"
        assert len(caplog.records) == 1
        assert (
            "File path a_bad/../relative_path may be unsafe due to unexpected relative navigation."
            in caplog.messages
        )


@pytest.mark.parametrize("filepath", PATHS_WITH_DOTS)
def test_make_path_safe_dots_warning(caplog, filepath):
    """Test that a user is warned about trailing dots in their file paths. The paths should remain unchanged."""
    with caplog.at_level(logging.WARNING):
        assert make_path_safe(filepath)[0] == filepath
        assert (
            f"File path {filepath} may be unsafe due to trailing dots."
            in caplog.messages
        )
