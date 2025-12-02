"""Tests for the Sangaboard thing."""

import pytest

from openflexure_microscope_server.things.stage.sangaboard import SangaboardThing


@pytest.fixture
def mock_sanga_thing(mocker):
    """Return a Sangaboard thing with a MagicMock for self._sangaboard."""
    sanga_thing = SangaboardThing()
    sanga_thing._sangaboard = mocker.MagicMock()
    return sanga_thing


def test_check_old_firmware(mock_sanga_thing):
    """Check firmware prior to version 1 throws a Runtime Error."""
    mock_sanga_thing._sangaboard.firmware_version.return_value = "0.1.1"
    with pytest.raises(RuntimeError):
        mock_sanga_thing.check_firmware()
