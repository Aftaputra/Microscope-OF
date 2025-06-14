"""
Test the SmartScanThing *without* connecting it to a LabThings Server.

By testing without connecting to the LabThings server it is possible to
directly poll any properties and to start any methods.

Any methods with LabThings dependency injections will require dependencies
to be passed in manually. Rather than passing in real LabThings clients
it is possible to create test objects that mock these clients. Thus, entirely
isolating one Thing for testing, at the expense of neededing to create detailed
mock objects.

For these tests to reliably represent real behaviour the mock Things will need to
be tested for matching signatures with dynamically generated clients.
"""

import tempfile
import os
import shutil
import logging

from fastapi import HTTPException
import pytest

from openflexure_microscope_server.things.smart_scan import (
    SmartScanThing,
    ScanNotRunningError,
)

# A global logger to pass in as an Invocation Logger
LOGGER = logging.getLogger("mock-invocation_logger")

# Use our own dir in the root temp dir not a dynamically generated one so we
# have some control of when it is deleted
SCAN_DIR = os.path.join(tempfile.gettempdir(), "scans")


def _clear_scan_dir():
    """Delete the scan dir"""
    if os.path.exists(SCAN_DIR):
        shutil.rmtree(SCAN_DIR)


@pytest.fixture
def smart_scan_thing():
    """Return a smart scan thing as a fixture"""
    return SmartScanThing(SCAN_DIR)


def test_initial_properties(smart_scan_thing):
    assert smart_scan_thing._scan_dir_manager.base_dir == SCAN_DIR
    assert smart_scan_thing.latest_scan_name is None


def test_inaccessible_scan_methods(smart_scan_thing):
    """The @_scan_running decorator should make some methods
    inaccessible unless a scan is running"""
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing._run_scan()
    with pytest.raises(ScanNotRunningError):
        smart_scan_thing._manage_stitching_threads()


def test_private_delete_scan(smart_scan_thing, caplog):
    """Test the private _delete_scan method deletes directories or warns if it can't"""

    _clear_scan_dir()
    with caplog.at_level(logging.INFO):
        fake_scan_name = "fake_scan_0001"
        fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)

        # Make the outer scan dir, but not the one to delete
        os.makedirs(SCAN_DIR)
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
    """Test the delete_scan API call deletes directories or warns if it can't"""

    _clear_scan_dir()
    with caplog.at_level(logging.INFO):
        fake_scan_name = "fake_scan_0001"
        fake_scan_path = os.path.join(SCAN_DIR, fake_scan_name)

        # Make the outer scan dir, but not the one to delete
        os.makedirs(SCAN_DIR)

        with pytest.raises(HTTPException) as exc_info:
            smart_scan_thing.delete_scan(fake_scan_name, LOGGER)
        # Should raise a 400 error if the scan doesn't exists, not a 404 as the server
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
