"""Test server booting and shut down."""

import os
import json
from copy import deepcopy

import pytest

from openflexure_microscope_server import server

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(THIS_DIR)
FULL_CONFIG = os.path.join(REPO_ROOT, "ofm_config_full.json")
SIM_CONFIG = os.path.join(REPO_ROOT, "ofm_config_simulation.json")


@pytest.mark.parametrize("side_effect", [None, RuntimeError("Mock")])
def test_monkey_patched_handle_exit(side_effect, mock_app, mocker):
    """Test that handle exit is monkey_patched."""
    # Setup the same for any side_effect
    # Create mocks for FastAPI.Server, and for our custom shutdown function
    mock_shutdown_func = mocker.Mock(side_effect=side_effect)
    mock_fastapi_server = mocker.patch.object(server, "Server")
    original_mock_handle_exit = mock_fastapi_server.handle_exit
    handle_exit_args = (mock_app, "mock_signal", "mock_frame")

    server.set_shutdown_function(mock_shutdown_func)

    if side_effect is None:
        # In normal operation, both the custom shutdown function and the original
        # handle_exit should be called
        server.Server.handle_exit(*handle_exit_args)

        assert mock_shutdown_func.call_count == 1
        assert original_mock_handle_exit.call_count == 1
        # Check arguments are propagated correctly.
        assert original_mock_handle_exit.call_args.args == handle_exit_args
    else:
        # Use an error side effect to check that our custom shutdown function is called
        # before the standard `handle_exit`
        with pytest.raises(RuntimeError, match="Mock"):
            server.Server.handle_exit(*handle_exit_args)
        # The error was raised so we know our custom function was run, check that
        # handle_exit wasn't
        assert original_mock_handle_exit.call_count == 0


def test_customise_server(mock_app, mocker):
    """Check that all server customisation stages are called."""
    # Mock everything to be called in customisation, partly setup may not be complete,
    # but also to limit excess coverage reporting.
    mocked_add_static = mocker.patch.object(server, "add_static_files")
    mocked_v2_endpoints = mocker.patch.object(server, "add_v2_endpoints")
    mocked_configure_logging = mocker.patch.object(server, "configure_logging")
    mocked_retrieve_log = mocker.patch.object(server, "retrieve_log")
    mocked_retrieve_log_file = mocker.patch.object(server, "retrieve_log_from_file")

    # Set up a mock server
    mock_server = mocker.Mock()
    mock_server.app = mock_app
    # The wrapper returned for app.get so we can see what functions are decorated.
    wrapper = mock_app.get.return_value

    # Finally we can run it!
    server.customise_server(mock_server, "mock_log_folder", "mock_scan_folder")

    # Check each internal customisation function is called
    assert mocked_add_static.call_count == 1
    assert mocked_v2_endpoints.call_count == 1
    assert mocked_configure_logging.call_count == 1
    # Check app.get adds two routes
    assert mock_app.get.call_count == 2
    assert wrapper.call_count == 2

    # Check the routes and functions are as expected.
    added_routes = [call.args[0] for call in mock_app.get.call_args_list]
    assert "/log/" in added_routes
    assert "/logfile/" in added_routes
    wrapped_functions = [call.args[0] for call in wrapper.call_args_list]
    assert mocked_retrieve_log in wrapped_functions
    assert mocked_retrieve_log_file


@pytest.mark.parametrize(
    "config_file, expected_scan_dir",
    [[FULL_CONFIG, "/var/openflexure/scans/"], [SIM_CONFIG, "./openflexure/scans/"]],
)
def test_get_scans_dir_ok(config_file, expected_scan_dir):
    """Test the _get_scans_dir function and also check the standard config files."""
    with open(config_file, "r", encoding="utf-8") as f_obj:
        config_dict = json.load(f_obj)
    assert server._get_scans_dir(config_dict) == expected_scan_dir


def test_get_scans_dir_no_smart_scan():
    """Test _get_scans_dir with no SmartScanThing."""
    # Load the standard config dict
    with open(FULL_CONFIG, "r", encoding="utf-8") as f_obj:
        config_dict = json.load(f_obj)
    # Delete smart scan
    del config_dict["things"]["/smart_scan/"]
    # No SmartScanThing, should return None
    assert server._get_scans_dir(config_dict) is None


def test_get_scans_dir_bad_smart_scan_config():
    """Test _get_scans_dir with a SmartScanThing that doesn't set a config dir."""
    # Load the standard config dict
    with open(FULL_CONFIG, "r", encoding="utf-8") as f_obj:
        config_dict = json.load(f_obj)

    # Copy the dictionary
    broken_config = deepcopy(config_dict)
    # Delete all the smart scan kwargs
    del broken_config["things"]["/smart_scan/"]["kwargs"]
    # Creates an Error
    with pytest.raises(RuntimeError):
        server._get_scans_dir(broken_config)

    # Same thing should happen if just the scans_folder key is deleted
    broken_config = deepcopy(config_dict)
    del broken_config["things"]["/smart_scan/"]["kwargs"]
    # Creates an Error
    with pytest.raises(RuntimeError):
        server._get_scans_dir(broken_config)
