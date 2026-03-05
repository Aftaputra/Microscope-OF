"""Unit tests for stitching command validation."""

import pytest

from openflexure_microscope_server.stitching import (
    StitcherValidationError,
    validate_command,
)


def test_validate_command_success():
    """Test valid commands pass validation."""
    validate_command(["openflexure-stitch", "--stitching_mode", "all", "path/to/scan"])
    validate_command(["--resize", "0.5", "8192"])


def test_validate_command_forbidden():
    """Test forbidden commands raise error."""
    with pytest.raises(
        StitcherValidationError, match="Forbidden element 'sudo' detected"
    ):
        validate_command(["sudo", "rm", "-rf", "/"])

    with pytest.raises(
        StitcherValidationError, match="Forbidden element 'python' detected"
    ):
        validate_command(["python", "-c", "print('hello')"])

    with pytest.raises(
        StitcherValidationError, match="Forbidden element 'sh' detected"
    ):
        validate_command(["sh", "-c", "whoami"])


def test_validate_command_unsafe_chars():
    """Test elements with unsafe characters raise error."""
    with pytest.raises(StitcherValidationError, match="contains unsafe characters"):
        validate_command(["openflexure-stitch", "path;rm -rf /"])

    with pytest.raises(StitcherValidationError, match="contains unsafe characters"):
        validate_command(["openflexure-stitch", "path&echo hello"])


def test_validate_command_case_insensitive():
    """Test forbidden command check is case-insensitive."""
    with pytest.raises(
        StitcherValidationError, match="Forbidden element 'SUDO' detected"
    ):
        validate_command(["SUDO", "ls"])
