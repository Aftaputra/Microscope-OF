"""Test that the code that talks to the external stitching process acts as expected.

This does not actually run stitching. Instead it checks that the expected commands are
generated, and the subprocess calling works as expected.
"""

import logging
from copy import copy

import pytest

from openflexure_microscope_server.stitching import (
    BaseStitcher,
    PreviewStitcher,
    FinalStitcher,
    STITCHING_RESOLUTION,
)

# A global logger pretending to be an Invocation Logger
LOGGER = logging.getLogger("mock-invocation_logger")
FAKE_DIR = "a/dir/that/is/fake"


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
        # check that a BaseSticher can't start
        with pytest.raises(NotImplementedError):
            stitcher.start()


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
    "--stitch-dzi",
    "--no-stitch_tiff",
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
    expected_command[6] = "0.36"
    expected_command[8] = "0.25"
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
    expected_command[6] = "0.36"
    expected_command[8] = "0.25"
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
