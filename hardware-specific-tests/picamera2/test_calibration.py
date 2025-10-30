"""Test data collection from the Raspberry Picamera."""

from copy import deepcopy
import tempfile

import pytest

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera.picamera import (
    MissingCalibrationError,
)

from .cam_test_utils import camera_test_client


def test_get_tuning_algo(picamera_thing):
    """Test that get_tuning algorithm retrieves tuning algorithms."""
    # Missing algorithm raises an error.
    with pytest.raises(MissingCalibrationError):
        picamera_thing.get_tuning_algo("foo")
    # Or returns None if explicitly told not to error.
    assert picamera_thing.get_tuning_algo("foo", raise_if_missing=False) is None

    # Real algorithm is a dict and contains expected keys
    assert isinstance(picamera_thing.get_tuning_algo("rpi.geq"), dict)
    assert "offset" in picamera_thing.get_tuning_algo("rpi.geq")

    # Set the tuning to None as it is technically optional. And check this
    # is handled gracefully. This needs to be done in a try block as LabThings
    # tries and fails to emit an event.
    try:
        picamera_thing.tuning = None
    except lt.exceptions.NotConnectedToServerError:
        # Labthings will complain that it is not connected to a server
        pass

    # Check it is set to None despite the above LabThings issue.
    assert picamera_thing.tuning is None

    # Raises an error as there is no tuning file set.
    with pytest.raises(MissingCalibrationError):
        picamera_thing.get_tuning_algo("rpi.geq")
    # Or returns None if explicitly told not to error.
    assert picamera_thing.get_tuning_algo("rpi.geq", raise_if_missing=False) is None


def test_calibration(picamera_thing, picamera_client):
    """Check that full auto calibrate completes and set the expected values."""
    # Check the calibration_required property used by the calibration wizard
    assert picamera_thing.calibration_required
    # Save copy of default tuning file for end of test
    original_default = deepcopy(picamera_thing.default_tuning)
    # Tuning should start the same as the server is loading with no settings.
    assert picamera_thing.default_tuning == picamera_thing.tuning
    # lens_shading tables should be None when loaded on default tuning as it is
    # adaptive
    assert picamera_thing.lens_shading_tables is None
    # The background detector isn't ready as there is no background image.
    assert not picamera_thing.background_detector_status.ready

    # Run full auto calibrate
    picamera_client.full_auto_calibrate()

    # After calibration it should report that calibration is no longer  required
    assert not picamera_thing.calibration_required
    # The tuning files should be different
    assert picamera_thing.default_tuning != picamera_thing.tuning
    # The default should be unchanged
    assert picamera_thing.default_tuning == original_default
    # Lens shading tables should no longer be None
    assert picamera_thing.lens_shading_tables is not None
    # There should be exactly one colour correction matrix
    # (no variations by colour temp)
    assert len(picamera_thing.get_tuning_algo("rpi.ccm")["ccms"]) == 1
    # Green equalisation offset should be set to maximum.
    assert picamera_thing.get_tuning_algo("rpi.geq")["offset"] == 65535
    assert picamera_thing.background_detector_status.ready


def test_tuning_is_persistent():
    """Check that tuning file adjustments are persistent."""
    # First check full auto-calibrate is persistent if same save dir is used.
    with tempfile.TemporaryDirectory() as tmpdir:
        with camera_test_client(settings_folder=tmpdir) as client:
            initial_tuning = deepcopy(client.tuning)
            client.full_auto_calibrate()
            calibrated_tuning = deepcopy(client.tuning)
            # Full auto calibrate should have saved the tuning.
            assert initial_tuning != calibrated_tuning

        # Reload the camera and server from scratch
        with camera_test_client(settings_folder=tmpdir) as client:
            initial_tuning = deepcopy(client.tuning)
            # On reload the initial tuning is as it was when calibrated last run
            assert initial_tuning == calibrated_tuning
            # Set the lens shading to be flat
            client.flat_lens_shading()
            flat_tuning = deepcopy(client.tuning)
            assert flat_tuning != calibrated_tuning

        # Reload to check the flat lst persists
        with camera_test_client(settings_folder=tmpdir) as client:
            initial_tuning = deepcopy(client.tuning)
            # On reload the initial tuning the flat tuning
            assert initial_tuning == flat_tuning
            # Reset the lens shading to what is in the default tuning file
            client.reset_lens_shading()
            flat_tuning = deepcopy(client.tuning)
            assert flat_tuning != calibrated_tuning

        # Reload the one more time to check the reset lst persists
        with camera_test_client(settings_folder=tmpdir) as client:
            initial_tuning = deepcopy(client.tuning)
            # On reload the initial tuning the flat tuning
            assert initial_tuning == flat_tuning
