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
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
from unittest import mock

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from labthings_fastapi.exceptions import InvocationCancelledError
from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.scan_directories import NotEnoughFreeSpaceError
from openflexure_microscope_server.stitching import StitchingSettings
from openflexure_microscope_server.things.scan_workflows import ScanWorkflow
from openflexure_microscope_server.things.smart_scan import (
    ActiveScanData,
    ScanNotRunningError,
    SmartScanThing,
)

# Use our own dir in the root temp dir not a dynamically generated one so we
# have some control of when it is deleted
SCAN_DIR = os.path.join(tempfile.gettempdir(), "smartscanthing")


def _clear_scan_dir() -> None:
    """Delete the scan dir."""
    if os.path.exists(SCAN_DIR):
        shutil.rmtree(SCAN_DIR)


@pytest.fixture
def entered_smart_scan_thing(smart_scan_thing):
    """Yield a smart scan thing as a fixture that has been entred.

    This will make a scan directory manager. This fixture also clears the scan dir
    """
    _clear_scan_dir()
    with smart_scan_thing:
        yield smart_scan_thing


def custom_smart_scan_thing(default_workflow, all_workflows, mocker):
    """Set up a custom smart scan thing with workflows adjusted.

    This allows setting a default workflow and to adjust all workflows from simple
    single item mock from `mock_all_slots`.
    """
    smart_scan_thing = create_thing_without_server(
        SmartScanThing,
        default_workflow=default_workflow,
        mock_all_slots=True,
    )
    interface_type = type(smart_scan_thing._thing_server_interface)
    interface_type.application_config = mocker.PropertyMock(
        return_value={"data_folder": tempfile.gettempdir()}
    )
    # Pop the existing mock workflow and add specified ones (if any)
    smart_scan_thing._all_workflows.pop("mock-_all_workflows")
    for key, thing in all_workflows.items():
        smart_scan_thing._all_workflows[key] = thing

    return smart_scan_thing


def test_initial_properties(entered_smart_scan_thing):
    """Check the initial values of properties.

    Test properties of SmartScanThing are available without a ThingServer
    and return expected default values.
    """
    smart_scan_thing = entered_smart_scan_thing
    assert smart_scan_thing._scan_dir_manager.base_dir == SCAN_DIR
    assert smart_scan_thing.latest_scan_name is None


@dataclass
class WorkflowSelectorTestCase:
    """The information from a capture in a smart_z_stack."""

    workflows: dict[str, mock.MagicMock]
    default_wf: str
    expected_wf: Optional[str]
    loaded_wf: Optional[str] = None
    side_effect: Optional[type | int | Iterable[int]] = None
    """The side effect of entering the Thing (None, Logger level number, Error type)"""
    match: Optional[str | Iterable[str]] = None


SELECTOR_CASES = [
    WorkflowSelectorTestCase(
        workflows={},
        default_wf="foo",
        expected_wf=None,
        side_effect=RuntimeError,
        match="Could not set Scan Workflow",
    ),
    WorkflowSelectorTestCase(
        workflows={
            "foo": mock.MagicMock(spec=ScanWorkflow),
            "bar": mock.MagicMock(spec=ScanWorkflow),
        },
        default_wf="foo",
        expected_wf="foo",
        side_effect=None,
    ),
    WorkflowSelectorTestCase(
        workflows={
            "foo": mock.MagicMock(spec=ScanWorkflow),
            "bar": mock.MagicMock(spec=ScanWorkflow),
        },
        default_wf="bar",
        expected_wf="bar",
        side_effect=None,
    ),
    WorkflowSelectorTestCase(
        workflows={
            "foo": mock.MagicMock(spec=ScanWorkflow),
            "bar": mock.MagicMock(spec=ScanWorkflow),
        },
        default_wf="wrong",
        expected_wf="foo",
        side_effect=logging.WARNING,
        match="Could not select default key 'wrong'",
    ),
    WorkflowSelectorTestCase(
        workflows={
            "foo": mock.MagicMock(spec=ScanWorkflow),
            "bar": mock.MagicMock(spec=ScanWorkflow),
        },
        default_wf="wrong",
        loaded_wf="bar",
        expected_wf="bar",
        side_effect=None,
    ),
    WorkflowSelectorTestCase(
        workflows={
            "foo": mock.MagicMock(spec=ScanWorkflow),
            "bar": mock.MagicMock(spec=ScanWorkflow),
        },
        default_wf="wrong",
        loaded_wf="wrong",
        expected_wf="foo",
        side_effect=[logging.WARNING, logging.WARNING],
        match=[
            "Could not select 'wrong' from Thing mapping",
            "Could not select default key 'wrong'",
        ],
    ),
]


@pytest.mark.parametrize("case", SELECTOR_CASES)
def test_workflow_set_on_enter(case, check_side_effect, mocker):
    """Check workflow is set on enter."""
    smart_scan_thing = custom_smart_scan_thing(case.default_wf, case.workflows, mocker)
    with check_side_effect(case.side_effect, match=case.match):
        # Load in "loaded" as the sever would
        smart_scan_thing._workflow_name = case.loaded_wf
        with smart_scan_thing:
            assert smart_scan_thing._workflow_name == case.expected_wf


def test_setting_workflows(caplog, mocker):
    """Check that setting workflow works, or warns if incorrect."""
    workflows = {
        "foo": mock.MagicMock(spec=ScanWorkflow),
        "bar": mock.MagicMock(spec=ScanWorkflow),
    }
    smart_scan_thing = custom_smart_scan_thing("foo", workflows, mocker)
    with caplog.at_level(logging.WARNING), smart_scan_thing:
        assert smart_scan_thing._workflow_name == "foo"
        assert smart_scan_thing._workflow is workflows["foo"]
        # Can't set None, raises a ValidationError
        with pytest.raises(ValidationError):
            smart_scan_thing.workflow_name = None
        # Empty string still won't change, but just warns
        smart_scan_thing.workflow_name = ""
        assert len(caplog.records) == 1
        assert smart_scan_thing._workflow_name == "foo"
        assert smart_scan_thing._workflow is workflows["foo"]
        # Can't set a different name
        smart_scan_thing.workflow_name = "wrong"
        assert len(caplog.records) == 2  # another log
        assert smart_scan_thing._workflow_name == "foo"
        assert smart_scan_thing._workflow is workflows["foo"]

        # can set a valid name
        smart_scan_thing.workflow_name = "bar"
        assert len(caplog.records) == 2  # No extra logs
        assert smart_scan_thing._workflow_name == "bar"
        assert smart_scan_thing._workflow is workflows["bar"]


def test_inaccessible_scan_methods(smart_scan_thing):
    """Test that method with @_scan_running decorator is inaccessible.

    The @_scan_running decorator makes these functions inaccessible unless
    a scan is running. Also test properties that raise same error.
    """
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing._run_scan()
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing._manage_stitching_threads()

    # Properties
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing.scan_data
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing.ongoing_scan


def test_private_delete_scan(entered_smart_scan_thing, caplog):
    """Test the private _delete_scan method deletes directories or warns if it can't."""
    smart_scan_thing = entered_smart_scan_thing
    with caplog.at_level(logging.INFO):
        fake_scan_name = "fake_scan_0001"
        fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)

        # Attempt to delete the fake scan. Expect it to fail and provide a warning
        deleted = smart_scan_thing._delete_scan(fake_scan_name)
        assert not deleted
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert caplog.records[0].name == "labthings_fastapi.things.smartscanthing"

        # Make a dir for the fake scan and delete it.
        os.makedirs(fake_scan_path)
        assert os.path.exists(fake_scan_path)
        deleted = smart_scan_thing._delete_scan(fake_scan_name)
        assert not os.path.exists(fake_scan_path)
        assert deleted
        # Check no extra logs generated
        assert len(caplog.records) == 1


def test_public_delete_scan(entered_smart_scan_thing, caplog):
    """Test the delete_scan API call deletes directories or warns if it can't."""
    smart_scan_thing = entered_smart_scan_thing
    with caplog.at_level(logging.INFO):
        fake_scan_name = "fake_scan_0001"
        fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)

        # Attempt to delete the fake scan. Expect it to fail
    with pytest.raises(HTTPException) as exc_info:
        smart_scan_thing.delete_scan(fake_scan_name)
    # Should raise a 400 error if the scan doesn't exist, not a 404 as the server
    # was not expecting to receive the scan files
    assert exc_info.value.status_code == 400
    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert caplog.records[0].name == "labthings_fastapi.things.smartscanthing"

    # Make a dir for the fake scan and delete it.
    os.makedirs(fake_scan_path)
    assert os.path.exists(fake_scan_path)
    smart_scan_thing.delete_scan(fake_scan_name)
    assert not os.path.exists(fake_scan_path)
    # Check no extra logs generated
    assert len(caplog.records) == 1


def test_delete_all_scans(entered_smart_scan_thing, caplog):
    """Check the delete_all_scan API really does delete all the scans."""
    smart_scan_thing = entered_smart_scan_thing
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
        smart_scan_thing.delete_all_scans()
        for fake_scan_name in fake_scan_names:
            fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)
            assert not os.path.exists(fake_scan_path)
        # No logs generated
        assert len(caplog.records) == 0


def _run_only_outer_scan(
    smart_scan_thing, mocker, adjust_initial_state: Optional[Callable] = None
):
    """Create a subclass of SmartScanThing to mock _run_scan and run sample_scan.

    This should do all the set up for a scan, move into the mocked
    _run_scan method where this can be tested. Once this is done
    the final scan behaviour can be tested too.

    adjust_initial_state is a callable which accepts the mocked smart scan thing
    as the only variable. It can be used to adjust the initial state of the test


    This seems hard to do with a fixture so it is being done with a private
    function
    """

    def check_locked(*_args, **_kwargs):
        """Check the scan is locked."""
        assert smart_scan_thing._scan_lock.locked()

    mocker.patch.object(smart_scan_thing, "_run_scan", side_effect=check_locked)
    mock_save_logs = mocker.patch(
        "openflexure_microscope_server.scan_directories.save_invocation_logs"
    )

    if adjust_initial_state is not None:
        adjust_initial_state(smart_scan_thing)

    exec_info = None
    try:
        smart_scan_thing.sample_scan(scan_name="FooBar")

    except Exception as e:
        exec_info = e

    assert not smart_scan_thing._scan_lock.locked()
    assert mock_save_logs.call_count >= 1

    # Return the mock thing for further state testing, and the
    # exec_info of any uncaught exceptions that were raised
    return smart_scan_thing, exec_info


def test_outer_scan(entered_smart_scan_thing, mocker):
    """Test setup and teardown of the scan."""
    mock_ss_thing, exec_info = _run_only_outer_scan(entered_smart_scan_thing, mocker)
    assert exec_info is None
    # Checked the mocked _run_scan was run exactly once
    assert mock_ss_thing._run_scan.call_count == 1


def test_outer_scan_wo_sample_skip(entered_smart_scan_thing, mocker):
    """Test setup and teardown of the scan."""

    def _set_skip_background(mock_ss_thing):
        # As the Thing is not connected to a server we set the setting via the internal
        # __dict__ to avoid triggering property emits that require a server
        mock_ss_thing.__dict__["skip_background"] = False

    mock_ss_thing, exec_info = _run_only_outer_scan(
        entered_smart_scan_thing, mocker, _set_skip_background
    )

    assert exec_info is None
    # Checked the mocked _run_scan was run exactly once
    assert mock_ss_thing._run_scan.call_count == 1


MOCK_SCAN_NAME = "test_name_0001"
MOCK_SCAN_DIR = "scans/test_name_0001/images/"
MOCK_START_POS = {"x": 123, "y": 456, "z": 789}


class MockWorkflowSettingModel(BaseModel):
    """A mock model to check that ActiveScanData can hold arbitrary models."""

    foo: str = "bar"
    bar: str = "foo"
    dx: int = 123
    dy: int = 456


def _expected_scan_data():
    """Return the expected ActiveScanData object for a SmartScan with default properties."""
    expected_dict = {
        "scan_name": MOCK_SCAN_NAME,
        "starting_position": MOCK_START_POS,
        "save_resolution": (1640, 1232),
        "stitch_automatically": True,
        "stitching_settings": {
            "overlap": 0.45,
            "correlation_resize": 0.5,
        },
        "workflow": "Mock",
        "workflow_settings": MockWorkflowSettingModel(),
    }
    return ActiveScanData(start_time=datetime.now(), **expected_dict)


@pytest.fixture
def scan_thing_mocked_for_scan_data(smart_scan_thing, mocker):
    """Return a scan thing that is mocked so that _collect_scan_data will run."""
    # Set the lock so it thinks the scan is running
    with smart_scan_thing._scan_lock:
        smart_scan_thing._stage.position = MOCK_START_POS

        smart_scan_thing._workflow.all_settings.return_value = (
            MockWorkflowSettingModel(),
            StitchingSettings(correlation_resize=0.5, overlap=0.45),
            (1640, 1232),
        )

        mock_ongoing_scan = mocker.Mock()
        mock_ongoing_scan.name = MOCK_SCAN_NAME
        mock_ongoing_scan.images_dir = MOCK_SCAN_DIR
        smart_scan_thing._ongoing_scan = mock_ongoing_scan
        smart_scan_thing._data_dir = "scans"

        yield smart_scan_thing


def test_collect_scan_data(scan_thing_mocked_for_scan_data):
    """Run _collect_scan_data, and check the ActiveScanData object has the expected values."""
    scan_thing = scan_thing_mocked_for_scan_data

    data = scan_thing._collect_scan_data(scan_thing._workflow)
    expected_data = _expected_scan_data()
    time_diff = expected_data.start_time - data.start_time
    assert abs(time_diff.total_seconds()) < 1
    # Set times to exactly the same before final comparison
    expected_data.start_time = data.start_time
    assert data == expected_data


def test_save_final_scan_data(scan_thing_mocked_for_scan_data):
    """Run _save_final_scan_data, check save is called with final results in ActiveScanData."""
    scan_thing = scan_thing_mocked_for_scan_data

    scan_thing._scan_data = scan_thing._collect_scan_data(scan_thing._workflow)
    scan_thing._scan_data.image_count = 44
    scan_thing._save_final_scan_data("Mocked!")
    # _ongoing_scan is a mock so we can check that save_scan data was called and get
    # the value
    scan_thing._ongoing_scan.save_scan_data.assert_called()
    final_data = scan_thing._ongoing_scan.save_scan_data.call_args[0][0]
    assert isinstance(final_data, ActiveScanData)
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
            scan_thing._scan_data = scan_thing._run_scan(scan_thing._workflow)
    else:
        with pytest.raises(expected_exception), caplog.at_level(logging.WARNING):
            scan_thing._scan_data = scan_thing._run_scan(scan_thing._workflow)
    # The preview stitcher object should still exist. And images dir should be set.
    assert scan_thing._preview_stitcher.images_dir == MOCK_SCAN_DIR

    final_scan_data = scan_thing._ongoing_scan.save_scan_data.call_args[0][0]
    calls = {
        "cam_change_streaming_mode_calls": scan_thing._cam.change_streaming_mode.call_count,
        "main_scan_loop_calls": scan_thing._main_scan_loop.call_count,
        "return_to_start_calls": scan_thing._return_to_starting_position.call_count,
        "perform_final_stitch_calls": scan_thing._perform_final_stitch.call_count,
        "save_scan_data_calls": scan_thing._ongoing_scan.save_scan_data.call_count,
    }
    return final_scan_data.scan_result, caplog.records, calls


def test_run_scan(scan_thing_mocked_for_run_scan, caplog):
    """Run _save_final_scan_data, check save is called with final results in ActiveScanData."""
    result, logs, calls = check_run_scan(scan_thing_mocked_for_run_scan, caplog)

    assert result == "success"
    assert len(logs) == 0

    expected_calls_numbers = {
        "cam_change_streaming_mode_calls": 2,
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
        "cam_change_streaming_mode_calls": 2,
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
        "cam_change_streaming_mode_calls": 2,
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
        "cam_change_streaming_mode_calls": 2,
        "main_scan_loop_calls": 1,
        "return_to_start_calls": 0,
        "perform_final_stitch_calls": 0,
        "save_scan_data_calls": 2,
    }
    assert calls == expected_calls_numbers
