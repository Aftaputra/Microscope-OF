"""Test the SmartScanThing *without* connecting it to a LabThings Server.

By testing without connecting to the LabThings server it is possible to
directly poll any properties and to start any methods.

Any methods with LabThings dependency injections will require dependencies
to be passed in manually. Rather than passing in real LabThings clients
it is possible to create test objects that mock these clients. Thus, entirely
isolating one Thing for testing, at the expense of needing to create detailed
mock objects.

For these tests to reliably represent real behaviour the mock Things will need to
be tested for matching signatures with dynamically generated clients.
"""

import logging
import os
import shutil
import tempfile
from datetime import datetime
from typing import Callable, Optional

import pytest
from fastapi import HTTPException

from labthings_fastapi.exceptions import InvocationCancelledError
from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.scan_directories import (
    NotEnoughFreeSpaceError,
    ScanData,
)
from openflexure_microscope_server.things.smart_scan import (
    ScanNotRunningError,
    SmartScanThing,
)

from .mock_things.mock_autofocus import MockAutoFocusThing
from .mock_things.mock_camera import MockCameraThing
from .mock_things.mock_csm import MockCSMThing
from .mock_things.mock_stage import MockStageThing

# A global logger to pass in as an Invocation Logger
LOGGER = logging.getLogger("mock-invocation_logger")

# Use our own dir in the root temp dir not a dynamically generated one so we
# have some control of when it is deleted
SCAN_DIR = os.path.join(tempfile.gettempdir(), "scans")


def _clear_scan_dir() -> None:
    """Delete the scan dir."""
    if os.path.exists(SCAN_DIR):
        shutil.rmtree(SCAN_DIR)


@pytest.fixture
def smart_scan_thing():
    """Return a smart scan thing as a fixture."""
    return create_thing_without_server(SmartScanThing, scans_folder=SCAN_DIR)


def test_initial_properties(smart_scan_thing):
    """Check the initial values of properties.

    Test properties of SmartScanThing are available without a ThingServer
    and return expected default values.
    """
    assert smart_scan_thing._scan_dir_manager.base_dir == SCAN_DIR
    assert smart_scan_thing.latest_scan_name is None


def test_inaccessible_scan_methods(smart_scan_thing):
    """Test that method with @_scan_running decorator is inaccessible.

    The @_scan_running decorator makes these functions inaccessible unless
    a scan is running.
    """
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing._run_scan()
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing._manage_stitching_threads()


def test_private_delete_scan(smart_scan_thing, caplog):
    """Test the private _delete_scan method deletes directories or warns if it can't."""
    _clear_scan_dir()
    with caplog.at_level(logging.INFO):
        fake_scan_name = "fake_scan_0001"
        fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)

        # Make the outer scan dir, but not the one to delete
        os.makedirs(SCAN_DIR)
        # Attempt to delete the fake scan. Expect it to fail and provide a warning
        deleted = smart_scan_thing._delete_scan(fake_scan_name, LOGGER)
        assert not deleted
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert caplog.records[0].name == "mock-invocation_logger"

        # Make a dir for the fake scan and delete it.
        os.makedirs(fake_scan_path)
        assert os.path.exists(fake_scan_path)
        deleted = smart_scan_thing._delete_scan(fake_scan_name, LOGGER)
        assert not os.path.exists(fake_scan_path)
        assert deleted
        # Check no extra logs generated
        assert len(caplog.records) == 1


def test_public_delete_scan(smart_scan_thing, caplog):
    """Test the delete_scan API call deletes directories or warns if it can't."""
    _clear_scan_dir()
    with caplog.at_level(logging.INFO):
        fake_scan_name = "fake_scan_0001"
        fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)

        # Make the outer scan dir, but not the one to delete
        os.makedirs(SCAN_DIR)

        # Attempt to delete the fake scan. Expect it to fail
    with pytest.raises(HTTPException) as exc_info:
        smart_scan_thing.delete_scan(fake_scan_name, LOGGER)
    # Should raise a 400 error if the scan doesn't exist, not a 404 as the server
    # was not expecting to receive the scan files
    assert exc_info.value.status_code == 400
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].name == "mock-invocation_logger"

    # Make a dir for the fake scan and delete it.
    os.makedirs(fake_scan_path)
    assert os.path.exists(fake_scan_path)
    smart_scan_thing.delete_scan(fake_scan_name, LOGGER)
    assert not os.path.exists(fake_scan_path)
    # Check no extra logs generated
    assert len(caplog.records) == 1


def test_delete_all_scans(smart_scan_thing, caplog):
    """Check the delete_all_scan API really does delete all the scans."""
    _clear_scan_dir()
    with caplog.at_level(logging.INFO):
        fake_scan_names = [
            "fake_scan_0001",
            "fake_scan_0002",
            "fake_scan_0003",
            "fake_scan_0004",
        ]
        for fake_scan_name in fake_scan_names:
            fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)
            os.makedirs(fake_scan_path)
            assert os.path.exists(fake_scan_path)
        smart_scan_thing.delete_all_scans(LOGGER)
        for fake_scan_name in fake_scan_names:
            fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)
            assert not os.path.exists(fake_scan_path)
        # No logs generated
        assert len(caplog.records) == 0


def _run_only_outer_scan(adjust_initial_state: Optional[Callable] = None):
    """Create a subclass of SmartScanThing to mock _run_scan and run sample_scan.

    This should do all the set up for a scan, move into the mocked
    _run_scan method where this can be tested. Once this is done
    the final scan behaviour can be tested too.

    adjust_initial_state is a callable which accepts the mocked smart scan thing
    as the only variable. It can be used to adjust the initial state of the test


    This seems hard to do with a fixture so it is being done with a private
    function
    """
    # cancel handle shouldn't be used. Set to arbitrary value for checking
    cancel_mock = 1  # not called
    af_mock = MockAutoFocusThing()
    stage_mock = MockStageThing()
    cam_mock = MockCameraThing()
    csm_mock = MockCSMThing()

    class MockedSmartScanThing(SmartScanThing):
        """Mocked version of SmartScanThing with a patched _run_scan method."""

        # Counter for checking functions were called
        mock_call_count = {"_run_scan": 0}

        def _run_scan(self):
            self.mock_call_count["_run_scan"] += 1

            """Check scan vars are set up as expected"""
            assert not self._scan_lock.acquire(timeout=0.1)
            assert self._cancel is cancel_mock
            assert self._scan_logger is LOGGER
            assert self._autofocus is af_mock
            assert self._stage is stage_mock
            assert self._cam is cam_mock
            assert self._csm is csm_mock

    # mock smart scan thing
    mock_ss_thing = create_thing_without_server(
        MockedSmartScanThing, scans_folder=SCAN_DIR
    )

    if adjust_initial_state is not None:
        adjust_initial_state(mock_ss_thing)

    exec_info = None
    try:
        mock_ss_thing.sample_scan(
            cancel=cancel_mock,  # Shouldn't be used, can be checked
            logger=LOGGER,
            autofocus=af_mock,
            stage=stage_mock,
            cam=cam_mock,
            csm=csm_mock,
            scan_name="FooBar",
        )
    except Exception as e:
        exec_info = e

    assert mock_ss_thing._scan_lock.acquire(timeout=0.1)
    mock_ss_thing._scan_lock.release()
    assert mock_ss_thing._cancel is None
    assert mock_ss_thing._scan_logger is None
    assert mock_ss_thing._autofocus is None
    assert mock_ss_thing._stage is None
    assert mock_ss_thing._cam is None
    assert mock_ss_thing._csm is None

    # Return the mock thing for further state testing, and the
    # exec_info of any uncaught exceptions that were raised
    return mock_ss_thing, exec_info


def test_outer_scan():
    """Test setup and teardown of the scan."""
    mock_ss_thing, exec_info = _run_only_outer_scan()
    assert exec_info is None
    # Checked the mocked _run_scan was run exactly once
    assert mock_ss_thing.mock_call_count["_run_scan"] == 1


def test_outer_scan_wo_sample_skip():
    """Test setup and teardown of the scan."""

    def _set_skip_background(mock_ss_thing):
        # As the Thing is not connected to a server we set the setting via the internal
        # __dict__ to avoid triggering property emits that require a server
        mock_ss_thing.__dict__["skip_background"] = False

    mock_ss_thing, exec_info = _run_only_outer_scan(_set_skip_background)

    assert exec_info is None
    # Checked the mocked _run_scan was run exactly once
    assert mock_ss_thing.mock_call_count["_run_scan"] == 1


MOCK_SCAN_NAME = "test_name_0001"
MOCK_SCAN_DIR = "scans/test_name_0001/images/"
MOCK_START_POS = {"x": 123, "y": 456, "z": 789}


def _expected_scan_data():
    """Return the expected ScanData object for a SmartScan with default properties."""
    expected_dict = {
        "scan_name": MOCK_SCAN_NAME,
        "starting_position": MOCK_START_POS,
        "overlap": 0.45,
        "max_dist": 45000,
        "dx": 100,
        "dy": 100,
        "autofocus_dz": 1000,
        "autofocus_on": True,
        "skip_background": True,
        "stitch_automatically": True,
        "correlation_resize": 0.5,
        "save_resolution": (1640, 1232),
    }
    return ScanData(start_time=datetime.now(), **expected_dict)


@pytest.fixture
def scan_thing_mocked_for_scan_data(smart_scan_thing, mocker):
    """Return a scan thing that is mocked so that _collect_scan_data will run."""
    # Give the scan thing a scan invocation logger so it thinks a scan is running.
    smart_scan_thing._scan_logger = LOGGER
    mocker.patch.object(
        smart_scan_thing, "_calc_displacement_from_test_image", return_value=[100, 100]
    )
    mock_ongoing_scan = mocker.Mock()
    type(mock_ongoing_scan).name = mocker.PropertyMock(return_value=MOCK_SCAN_NAME)
    type(mock_ongoing_scan).images_dir = mocker.PropertyMock(return_value=MOCK_SCAN_DIR)
    mock_stage = mocker.Mock()
    type(mock_stage).position = mocker.PropertyMock(return_value=MOCK_START_POS)

    mock_autofocus = mocker.Mock()

    smart_scan_thing._ongoing_scan = mock_ongoing_scan
    smart_scan_thing._stage = mock_stage
    smart_scan_thing._autofocus = mock_autofocus
    return smart_scan_thing


def test_collect_scan_data(scan_thing_mocked_for_scan_data):
    """Run _collect_scan_data, and check the ScanData object has the expected values."""
    scan_thing = scan_thing_mocked_for_scan_data

    data = scan_thing._collect_scan_data()
    expected_data = _expected_scan_data()
    time_diff = expected_data.start_time - data.start_time
    assert abs(time_diff.total_seconds()) < 1
    # Set times to exactly the same before final comparison
    expected_data.start_time = data.start_time
    assert data == expected_data


def test_save_final_scan_data(scan_thing_mocked_for_scan_data):
    """Run _save_final_scan_data, check save is called with final results in ScanData."""
    scan_thing = scan_thing_mocked_for_scan_data

    scan_thing._scan_data = scan_thing._collect_scan_data()
    scan_thing._scan_data.image_count = 44
    scan_thing._save_final_scan_data("Mocked!")
    # _ongoing_scan is a mock so we can check that save_scan data was called and get
    # the value
    scan_thing._ongoing_scan.save_scan_data.assert_called()
    final_data = scan_thing._ongoing_scan.save_scan_data.call_args[0][0]
    assert isinstance(final_data, ScanData)
    assert final_data.scan_result == "Mocked!"
    assert final_data.image_count == 44
    assert final_data.duration.total_seconds() < 1


@pytest.fixture
def scan_thing_mocked_for_run_scan(scan_thing_mocked_for_scan_data, mocker):
    """Return a scan_thing mocked so _run_scan works.

    main_scan_loop(), _return_to_starting_position(), and _perform_final_stitch() are
    Mocks and _cam is a MockCameraThing
    """
    scan_thing = scan_thing_mocked_for_scan_data
    scan_thing._cam = MockCameraThing()
    mocker.patch.object(scan_thing, "_cancel")
    mocker.patch.object(scan_thing, "_main_scan_loop")
    mocker.patch.object(scan_thing, "_return_to_starting_position")
    mocker.patch.object(scan_thing, "_perform_final_stitch")

    return scan_thing


def check_run_scan(scan_thing, caplog, expected_exception=None):
    """Run _run_scan with a mocked scan_thing, capture logs and call counts.

    This can be used to check how run_scan executes in different exit modes.
    A separate tests is above for scan completing with no exception.

    :returns: a tuple of:

        * The final result as reported in scan_data
        * The logging records
        * a dictionary of call counts
    """
    if expected_exception is None:
        with caplog.at_level(logging.WARNING):
            scan_thing._scan_data = scan_thing._run_scan()
    else:
        with pytest.raises(expected_exception), caplog.at_level(logging.WARNING):
            scan_thing._scan_data = scan_thing._run_scan()
    # The preview stitcher object should still exist. And images dir should be set.
    assert scan_thing._preview_stitcher.images_dir == MOCK_SCAN_DIR

    final_scan_data = scan_thing._ongoing_scan.save_scan_data.call_args[0][0]
    calls = {
        "cam_start_streaming_calls": scan_thing._cam.start_streaming.call_count,
        "main_scan_loop_calls": scan_thing._main_scan_loop.call_count,
        "return_to_start_calls": scan_thing._return_to_starting_position.call_count,
        "perform_final_stitch_calls": scan_thing._perform_final_stitch.call_count,
        "save_scan_data_calls": scan_thing._ongoing_scan.save_scan_data.call_count,
    }
    return final_scan_data.scan_result, caplog.records, calls


def test_run_scan(scan_thing_mocked_for_run_scan, caplog):
    """Run _save_final_scan_data, check save is called with final results in ScanData."""
    result, logs, calls = check_run_scan(scan_thing_mocked_for_run_scan, caplog)

    assert result == "success"
    assert len(logs) == 0

    expected_calls_numbers = {
        "cam_start_streaming_calls": 2,
        "main_scan_loop_calls": 1,
        "return_to_start_calls": 1,
        "perform_final_stitch_calls": 1,
        "save_scan_data_calls": 2,
    }
    assert calls == expected_calls_numbers


def test_run_scan_err_in_main_loop(scan_thing_mocked_for_run_scan, caplog, mocker):
    """Check correct methods called if main_loop errors."""
    scan_thing = scan_thing_mocked_for_run_scan
    mocker.patch.object(
        scan_thing, "_main_scan_loop", side_effect=FileNotFoundError("mocked")
    )

    result, logs, calls = check_run_scan(scan_thing, caplog, FileNotFoundError)

    assert result.startswith("FileNotFoundError:")
    assert len(logs) == 1
    assert logs[0].levelno == logging.ERROR

    # Main loop not run, nor are return to start, final stitch, or purging of empty
    # scans. Save scan data is still called twice
    expected_calls_numbers = {
        "cam_start_streaming_calls": 2,
        "main_scan_loop_calls": 1,
        "return_to_start_calls": 0,
        "perform_final_stitch_calls": 0,
        "save_scan_data_calls": 2,
    }
    assert calls == expected_calls_numbers


def test_run_scan_cancelled(scan_thing_mocked_for_run_scan, caplog, mocker):
    """Check correct methods called scan is cancelled."""
    scan_thing = scan_thing_mocked_for_run_scan
    mocker.patch.object(
        scan_thing, "_main_scan_loop", side_effect=InvocationCancelledError()
    )

    result, logs, calls = check_run_scan(scan_thing, caplog)

    assert result == "cancelled by user"
    # No logs at warning level.
    assert len(logs) == 0

    # Main loop not run, nor are return to start, final stitch, or purging of empty
    # scans. Save scan data is still called twice
    expected_calls_numbers = {
        "cam_start_streaming_calls": 2,
        "main_scan_loop_calls": 1,
        "return_to_start_calls": 1,
        "perform_final_stitch_calls": 1,
        "save_scan_data_calls": 2,
    }
    assert calls == expected_calls_numbers


def test_run_scan_fill_disk(scan_thing_mocked_for_run_scan, caplog, mocker):
    """Check correct methods called if disk fills up."""
    scan_thing = scan_thing_mocked_for_run_scan
    mocker.patch.object(
        scan_thing, "_main_scan_loop", side_effect=NotEnoughFreeSpaceError()
    )

    result, logs, calls = check_run_scan(scan_thing, caplog, NotEnoughFreeSpaceError)

    assert result.startswith("NotEnoughFreeSpaceError:")
    assert len(logs) == 1
    assert logs[0].levelno == logging.ERROR

    # Main loop not run, nor are return to start, final stitch, or purging of empty
    # scans. Save scan data is still called twice
    expected_calls_numbers = {
        "cam_start_streaming_calls": 2,
        "main_scan_loop_calls": 1,
        "return_to_start_calls": 0,
        "perform_final_stitch_calls": 0,
        "save_scan_data_calls": 2,
    }
    assert calls == expected_calls_numbers
