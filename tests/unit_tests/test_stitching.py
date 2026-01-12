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

import labthings_fastapi as lt

from openflexure_microscope_server.stitching import (
    STITCHING_RESOLUTION,
    BaseStitcher,
    FinalStitcher,
    PreviewStitcher,
    StitcherValidationError,
)

from ..shared_utils.lt_test_utils import LabThingsTestEnv

# A global logger pretending to the logger from a thing
LOGGER = logging.getLogger("mock-thing_logger")
FAKE_DIR: list[str] = os.path.join("a", "dir", "that", "is", "fake")
THIS_DIR: str = os.path.dirname(os.path.realpath(__file__))
MOCK_STITCHER: str = os.path.join(THIS_DIR, "mock_stitching", "mock-stitch.py")


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


def test_final_stitcher_command_defaults(caplog):
    """Check the FinalStitcher stitches with expected default values.

    It should warn when default values are used as they are a fallback.
    """
    n_logs = 0
    # Test with no dictionary data and with irrelevant dictionary data.
    with caplog.at_level(logging.WARNING):
        for data_dict in [None, {"irrelevant": "data"}]:
            stitcher = FinalStitcher(FAKE_DIR, logger=LOGGER, scan_data_dict=data_dict)
            # Should log for overlap being None and correlation_resize being None
            n_logs += 2
            assert len(caplog.records) == n_logs
        assert stitcher.command == FINAL_EXPECTED_COMMAND


def test_final_stitcher_command_tiff(caplog):
    """Check that the tiff can be requested."""
    # Modify defaults
    expected_command = copy(FINAL_EXPECTED_COMMAND)
    expected_command[4] = "--stitch_tiff"
    stitcher = FinalStitcher(FAKE_DIR, logger=LOGGER, stitch_tiff=True)
    # Should log for overlap being None and correlation_resize being None
    assert len(caplog.records) == 2
    assert stitcher.command == expected_command


def test_final_stitcher_command_set_val_directly():
    """Check that values are set as expected when directly input."""
    # Modify defaults
    expected_command = copy(FINAL_EXPECTED_COMMAND)
    expected_command[8] = "0.36"
    expected_command[10] = "0.25"
    # Test with no data dictionary, irrelevant data, and also the wrong data
    # When wrong data is submitted, it should take the directly input data.
    dict_vals = [
        None,
        {"irrelevant": "data"},
        {"overlap": 0.2, "save_resolution": [5, 5]},
    ]
    for data_dict in dict_vals:
        stitcher = FinalStitcher(
            FAKE_DIR,
            logger=LOGGER,
            overlap=0.4,
            correlation_resize=0.25,
            scan_data_dict=data_dict,
        )
        assert stitcher.command == expected_command


def test_final_stitcher_command_set_with_dict():
    """Check that values are set as expected when set from a ScanData dictionary."""
    # Modify defaults
    expected_command = copy(FINAL_EXPECTED_COMMAND)
    expected_command[8] = "0.36"
    expected_command[10] = "0.25"
    # Check same thing works with a dictionary, resize is calculated from the saved image
    # resolution. Make 4x bigger than STITCHING_RESOLUTION to get 0.25
    resolution = [dim * 4 for dim in STITCHING_RESOLUTION]
    # Check legacy key as well as current one:
    for resolution_key in ["save_resolution", "capture resolution"]:
        stitcher = FinalStitcher(
            FAKE_DIR,
            logger=LOGGER,
            scan_data_dict={"overlap": 0.4, resolution_key: resolution},
        )
        assert stitcher.command == expected_command


def _validation_error_tester(scan_path, **kwargs):
    """Check each type of stitcher throws a validation error for the given init args."""
    # If scan_data_dict is in the kwargs only test the scan_data_dict
    if "scan_data_dict" not in kwargs:
        with pytest.raises(StitcherValidationError):
            BaseStitcher(scan_path, **kwargs).command
        with pytest.raises(StitcherValidationError):
            PreviewStitcher(scan_path, **kwargs).command
    with pytest.raises(StitcherValidationError):
        FinalStitcher(scan_path, logger=LOGGER, **kwargs).command


def test_validation_error():
    """Test a number of ways to try to inject malicious arguments into the stitcher.

    The stitcher should throw a validation error each attempt.
    """
    _validation_error_tester("/dir;rm -rf /;", overlap=".2", correlation_resize=".25")
    _validation_error_tester(FAKE_DIR, overlap=".2", correlation_resize=".25;rm -rf /;")
    _validation_error_tester(FAKE_DIR, overlap=".2;rm -rf /;", correlation_resize=".25")
    _validation_error_tester(FAKE_DIR, scan_data_dict={"overlap": ".2;rm -rf /;"})


def test_extra_arg_validation():
    """Test that malicious arguments in extra_args also throw validation error.

    Currently extra args do not come from user input. But this makes checks more
    future-proof.
    """
    stitcher = FinalStitcher(FAKE_DIR, logger=LOGGER)
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
        stitcher = FinalStitcher(FAKE_DIR, logger=self.logger)
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
        # Input values to prevent logging
        stitcher = FinalStitcher(
            FAKE_DIR, logger=LOGGER, overlap=0.1, correlation_resize=0.5
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


def test_final_stitching_command_error(caplog, mocker):
    """Check that ChildProcessError is raised if the final stitch errors."""
    mock_cmd = f"python {MOCK_STITCHER}"

    mocker.patch("openflexure_microscope_server.stitching.STITCHING_CMD", mock_cmd)

    with caplog.at_level(logging.INFO):
        stitcher = FinalStitcher(FAKE_DIR, logger=LOGGER)
        # Send in the argument ERROR to mock-stitch and it will raise an error rather
        # than echo.
        stitcher._extra_args = ["ERROR"]
        with pytest.raises(ChildProcessError):
            stitcher.run()
