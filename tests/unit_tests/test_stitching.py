"""Test that the code that talks to the external stitching process acts as expected.

This does not actually run stitching. Instead it checks that the expected commands are
generated, and the subprocess calling works as expected.
"""

import logging
import os
import re
import time
from copy import copy

import pytest
from pydantic import BaseModel

import labthings_fastapi as lt

from openflexure_microscope_server.stitching import (
    FORBIDDEN_COMMANDS,
    BaseStitcher,
    FinalStitcher,
    PreviewStitcher,
    StitcherValidationError,
    StitchingSettings,
    validate_command,
)

from ..shared_utils.lt_test_utils import LabThingsTestEnv

# A global logger pretending to the logger from a thing
LOGGER = logging.getLogger("mock-thing_logger")
FAKE_DIR: list[str] = os.path.join("a", "dir", "that", "is", "fake")
THIS_DIR: str = os.path.dirname(os.path.realpath(__file__))
MOCK_STITCHER: str = os.path.join(THIS_DIR, "mock_stitching", "mock-stitch.py")


def test_validate_command_success():
    """Test valid commands pass validation."""
    validate_command(["openflexure-stitch", "--stitching_mode", "all", "path/to/scan"])
    validate_command(["--resize", "0.5", "8192"])


@pytest.mark.parametrize("cmd_name", FORBIDDEN_COMMANDS)
def test_validate_command_forbidden(cmd_name):
    """Test forbidden commands raise error."""
    # As the main command
    with pytest.raises(
        StitcherValidationError, match=f"Forbidden element '{cmd_name}' detected"
    ):
        validate_command([cmd_name, "some_arg"])

    # As an argument (case-insensitive)
    with pytest.raises(
        StitcherValidationError, match=f"Forbidden element '{cmd_name.upper()}' detected"
    ):
        validate_command(["safe-command", cmd_name.upper()])


def test_base_stitcher():
    """Test the logic in BaseStitcher.

    Pretty much the only logic in base stitcher is forming a command, and calculating
    the min_overlap from overlap.

    The BaseStitcher can't start as the start method is explicitly NotImplemented.
    """
    # Overlaps and expected minimum overlap to be in command line argument.
    overlaps = [(0.1, "0.09"), (0.4, "0.36"), (0.8, "0.72")]

    for overlap, min_overlap in overlaps:
        expected_command = [
            "openflexure-stitch",
            "--stitching_mode",
            "all",
            "--minimum_overlap",
            min_overlap,
            "--resize",
            "0.5",
            FAKE_DIR,
        ]
        stitcher = BaseStitcher(FAKE_DIR, overlap=overlap, correlation_resize=0.5)
        assert stitcher.command == expected_command


def test_preview_stitcher_command():
    """Check preview stitcher command for a specific example."""
    expected_command = [
        "openflexure-stitch",
        "--stitching_mode",
        "preview_stitch",
        "--minimum_overlap",
        "0.09",
        "--resize",
        "0.5",
        FAKE_DIR,
    ]
    stitcher = PreviewStitcher(FAKE_DIR, overlap=0.1, correlation_resize=0.5)
    assert stitcher.command == expected_command


FINAL_EXPECTED_COMMAND = [
    "openflexure-stitch",
    "--stitching_mode",
    "all",
    "--stitch_dzi",
    "--no-stitch_tiff",
    "--tile_size",
    "8192",
    "--minimum_overlap",
    "0.09",
    "--resize",
    "0.5",
    FAKE_DIR,
]

DEFAULT_SETTINGS = StitchingSettings(correlation_resize=0.5, overlap=0.1)


def test_final_stitcher_command_tiff():
    """Check that the tiff can be requested."""
    # Modify defaults
    expected_command = copy(FINAL_EXPECTED_COMMAND)
    expected_command[4] = "--stitch_tiff"
    stitcher = FinalStitcher(
        FAKE_DIR, logger=LOGGER, stitching_settings=DEFAULT_SETTINGS, stitch_tiff=True
    )
    assert stitcher.command == expected_command


def test_final_stitcher_command_with_settings():
    """Check that values are set as expected when set from a ScanData dictionary."""
    # Modify defaults
    expected_command = copy(FINAL_EXPECTED_COMMAND)
    expected_command[8] = "0.36"
    expected_command[10] = "0.25"

    stitcher = FinalStitcher(
        FAKE_DIR,
        logger=LOGGER,
        stitching_settings=StitchingSettings(correlation_resize=0.25, overlap=0.4),
    )
    assert stitcher.command == expected_command


def _validation_error_tester(scan_path, **kwargs):
    """Check stitcher throws a validation error for the given init args."""
    with pytest.raises(StitcherValidationError):
        BaseStitcher(scan_path, **kwargs).command
    with pytest.raises(StitcherValidationError):
        PreviewStitcher(scan_path, **kwargs).command


def test_validation_error():
    """Test a number of ways to try to inject malicious arguments into the stitcher.

    The stitcher should throw a validation error each attempt.
    """
    # Tests for preview (and base) stitcher
    _validation_error_tester("/dir;rm -rf /;", overlap=".2", correlation_resize=".25")
    _validation_error_tester(FAKE_DIR, overlap=".2", correlation_resize=".25;rm -rf /;")
    _validation_error_tester(FAKE_DIR, overlap=".2;rm -rf /;", correlation_resize=".25")

    class EvilModel(BaseModel):
        overlap: str
        correlation_resize: str

    with pytest.raises(StitcherValidationError):
        FinalStitcher(
            FAKE_DIR,
            logger=LOGGER,
            stitching_settings=EvilModel(
                overlap=".2;rm -rf /;", correlation_resize=".25"
            ),
        )


def test_extra_arg_validation():
    """Test that malicious arguments in extra_args also throw validation error.

    Currently extra args do not come from user input. But this makes checks more
    future-proof.
    """
    stitcher = FinalStitcher(
        FAKE_DIR, logger=LOGGER, stitching_settings=DEFAULT_SETTINGS
    )
    stitcher._extra_args = ["&&rm -rf /&&"]
    with pytest.raises(StitcherValidationError):
        stitcher.command


def test_preview_stitching_command(caplog, mocker):
    """Check the preview process runs in a background thread and doesn't log."""
    mock_cmd = "python -m mock_command.py"

    mocker.patch("openflexure_microscope_server.stitching.STITCHING_CMD", mock_cmd)

    with caplog.at_level(logging.INFO):
        stitcher = PreviewStitcher(FAKE_DIR, overlap=0.1, correlation_resize=0.5)
        stitcher.start()
        # Should take a second or so to run so will still be running
        assert stitcher.running
        # Can't start another time, instead get a runtime error
        with pytest.raises(RuntimeError):
            stitcher.start()
        # Wait for it to complete
        stitcher.wait()
        # It is now not running
        assert not stitcher.running
        assert len(caplog.records) == 0


class StitchingTestThing(lt.Thing):
    """A Thing for running stitching in invocation threads.

    This is needed to check cancellation behaviour.
    """

    @lt.action
    def run_preview(self):
        """Run the preview stitcher."""
        stitcher = PreviewStitcher(FAKE_DIR, overlap=0.1, correlation_resize=0.5)
        # Send in the argument HANG to mock-stitch and it just hang for 10s
        stitcher._extra_args = ["HANG"]
        stitcher.start()
        stitcher.wait()

    @lt.action
    def run_final(self):
        """Run the final stitcher."""
        stitcher = FinalStitcher(
            FAKE_DIR, logger=self.logger, stitching_settings=DEFAULT_SETTINGS
        )
        # Send in the argument HANG to mock-stitch and it just hang for 10s
        stitcher._extra_args = ["HANG"]
        stitcher.run()


@pytest.fixture
def stitching_test_env():
    """Return a test environment for a server with just StitchingTestThing."""
    with LabThingsTestEnv(things={"stitcher": StitchingTestThing}) as env:
        yield env


def test_preview_stitching_cancelled(stitching_test_env, mocker):
    """Check that preview stitch can be cancelled."""
    mock_cmd = f"python {MOCK_STITCHER}"

    mocker.patch("openflexure_microscope_server.stitching.STITCHING_CMD", mock_cmd)

    t_start = time.time()
    # Start the action
    response = stitching_test_env.start_action("stitcher", "run_preview")
    # Sleep long enough for at least 1 log.
    time.sleep(0.5)
    # Cancel using a DELETE request
    stitching_test_env.cancel_action(response)
    invocation_data = stitching_test_env.poll_action(response)

    # If it wasn't cancelled it would hang for 10 s. Here we check the cancel killed
    # it within 2s.
    assert time.time() - t_start < 2
    assert invocation_data["status"] == "cancelled"
    logs = invocation_data["log"]
    assert len(logs) == 1
    assert re.match(r"^Invocation [0-9a-f-]+ was cancelled", logs[0]["message"])


def test_final_stitching_command(caplog, mocker):
    """Check the final stitch runs until completion, and print statements are logged."""
    mock_cmd = f"python {MOCK_STITCHER}"

    mocker.patch("openflexure_microscope_server.stitching.STITCHING_CMD", mock_cmd)

    with caplog.at_level(logging.INFO):
        stitcher = FinalStitcher(
            FAKE_DIR, logger=LOGGER, stitching_settings=DEFAULT_SETTINGS
        )
        # For the final stitcher it will always complete before returning.
        stitcher.run()
        # The mock command logs the inputs (but not the initial command) and the
        # stitcher logs # "Stitching complete" when it ends.
        assert len(caplog.records) == len(FINAL_EXPECTED_COMMAND)
        for i, record in enumerate(caplog.records):
            msg = record.message.strip()
            if i == len(FINAL_EXPECTED_COMMAND) - 1:
                assert msg == "Stitching complete"
            else:
                assert msg == FINAL_EXPECTED_COMMAND[i + 1]


def test_final_stitching_command_cancelled(stitching_test_env, mocker):
    """Check that final stitch can be cancelled."""
    mock_cmd = f"python {MOCK_STITCHER}"

    mocker.patch("openflexure_microscope_server.stitching.STITCHING_CMD", mock_cmd)

    # Start the action
    response = stitching_test_env.start_action("stitcher", "run_final")
    # Sleep long enough for at least 1 log.
    time.sleep(0.5)
    # Cancel using a DELETE request
    stitching_test_env.cancel_action(response)
    invocation_data = stitching_test_env.poll_action(response)

    assert invocation_data["status"] == "cancelled"
    logs = invocation_data["log"]
    assert len(logs) < len(FINAL_EXPECTED_COMMAND) + 1
    assert logs[-2]["message"] == "Stitching cancelled by user"
    assert re.match(r"^Invocation [0-9a-f-]+ was cancelled", logs[-1]["message"])


def test_final_stitching_command_error(mocker):
    """Check that ChildProcessError is raised if the final stitch errors."""
    mock_cmd = f"python {MOCK_STITCHER}"

    mocker.patch("openflexure_microscope_server.stitching.STITCHING_CMD", mock_cmd)

    stitcher = FinalStitcher(
        FAKE_DIR, logger=LOGGER, stitching_settings=DEFAULT_SETTINGS
    )
    # Send in the argument ERROR to mock-stitch and it will raise an error rather
    # than echo.
    stitcher._extra_args = ["ERROR"]
    with pytest.raises(ChildProcessError):
        stitcher.run()
