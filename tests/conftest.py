"""Fixtures for all test suites."""

import json
import logging
import os
import re
import tempfile
from collections.abc import Iterable
from contextlib import contextmanager
from typing import Optional

import pytest

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things.smart_scan import (
    SmartScanThing,
)

from .shared_utils.lt_test_utils import LabThingsTestEnv

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS_DIR)
SIM_CONFIG = os.path.join(REPO_ROOT, "ofm_config_simulation.json")


@pytest.fixture
def simulation_test_env():
    """Yield a server with the configuration from the simulation json."""
    with open(SIM_CONFIG, "r", encoding="utf-8") as f_obj:
        config_dict = json.load(f_obj)
    with LabThingsTestEnv(
        things=config_dict["things"],
        application_config=config_dict["application_config"],
    ) as env:
        yield env


@pytest.fixture
def check_side_effect(caplog):
    """Supply a context manager for checking code either logs, raises an error, or doesn't."""

    @contextmanager
    def _checker(
        side_effect: Optional[type | int | Iterable[int]],
        match: Optional[str | Iterable[str]] = None,
    ) -> None:
        """Check the code within this context has the expected side effect.

        :param side_effect: The side effect of the code within this context. An int
            should be a logging level number, or a list of level numbers if multiple
            logs are expected.
        :param match: Optionally a match regex for raises or the logger, can be a list
            if side effect is a list of levels.
        """
        # If the side effect is an exception
        if isinstance(side_effect, type) and issubclass(side_effect, BaseException):
            with pytest.raises(side_effect, match=match):
                yield
            return

        # If the side effect is None or logging
        caplog.clear()

        with caplog.at_level(logging.INFO):
            yield

        if side_effect is None:
            # No side effect
            assert caplog.records == []
        elif isinstance(side_effect, Iterable):
            # Multiple logs
            if match is not None:
                assert isinstance(match, Iterable)
                assert len(match) == len(side_effect)
            assert len(caplog.records) == len(side_effect)
            for i, level in enumerate(side_effect):
                record = caplog.records[i]
                assert record.levelno == level
                if match is not None:
                    assert re.match(match[i], record.message) is not None
        else:
            # Single log
            assert len(caplog.records) == 1
            record = caplog.records[0]
            assert record.levelno == side_effect
            if match is not None:
                assert re.match(match, record.message) is not None

    return _checker


@pytest.fixture
def mock_picam_thing(mocker):
    """Import PiCamera without hardware well enough to get a ThingDescription."""
    dummy_cam = mocker.Mock()
    mock_picamera2 = mocker.MagicMock()
    mock_picamera2.return_value.__enter__.return_value = dummy_cam
    mock_picamera2.return_value.__exit__.return_value = None

    mocker.patch.dict(
        "sys.modules",
        {
            "picamera2": mock_picamera2,
            "picamera2.encoders": mocker.Mock(),
            "picamera2.outputs": mocker.Mock(),
        },
    )

    from openflexure_microscope_server.things.camera.picamera import PiCameraV2

    return create_thing_without_server(PiCameraV2)


@pytest.fixture
def smart_scan_thing(mocker):
    """Return a smart scan thing as a fixture."""
    thing = create_thing_without_server(
        SmartScanThing,
        default_workflow="mock-_all_workflows",
        mock_all_slots=True,
    )
    type(thing._thing_server_interface).application_config = mocker.PropertyMock(
        return_value={"data_folder": tempfile.gettempdir()}
    )
    return thing
