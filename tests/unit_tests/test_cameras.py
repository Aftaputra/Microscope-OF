"""Tests for camera classes. These tests focus on checking the camera APIs are equivalent.

Tests for specific camera hardware are in the hardware_specific_tests directory. Tests
on camera functionality using the simulation camera are in "test_camera".
"""

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things.camera import BaseCamera
from openflexure_microscope_server.things.camera.opencv import OpenCVCamera
from openflexure_microscope_server.things.camera.simulation import SimulatedCamera


def _get_clean_camera_description(camera_thing):
    """Return actions and properties for a camera Thing, separating those exposed to the UI.

    Return cleaned sets of actions and properties for camera_thing, excluding
    calibration actions exposed to the UI as primary or secondary calibration actions,
    and excluding the properties exposed in manual camera settings.

    :returns: Dict with keys:

        * "actions" - Actions not explicitly exposed to the UI by this camera.
        * "properties" - Properties not explicitly exposed to the UI as manual camera
            settings.
        * "calibration_actions" - Actions explicitly exposed to the UI by this camera.
        * "manual_properties" - Properties explicitly exposed to the UI as manual
            camera settings.
    """
    td = camera_thing.thing_description()
    actions = set(td.actions.keys())
    properties = set(td.properties.keys())

    # Calibration actions are camera specific
    primary = [btn.action for btn in camera_thing.primary_calibration_actions]
    secondary = [btn.action for btn in camera_thing.secondary_calibration_actions]
    calibration_actions = set(primary + secondary)

    actions -= calibration_actions

    # Manual properties are also camera specific
    manual_props = {ctrl.property_name for ctrl in camera_thing.manual_camera_settings}
    properties -= manual_props

    return {
        "actions": actions,
        "properties": properties,
        "calibration_actions": calibration_actions,
        "manual_properties": manual_props,
    }


def test_thing_description_equivalence(mock_picam_thing):
    """Ensure the built-in camera Thing subclasses retain consistent core functionality.

    This test verifies that extra actions are not unintentionally introduced to
    camera child classes. Any addition of actions must be accompanied by an update
    to this test, prompting discussion of whether the action belongs in the subclass
    or the base camera class.
    """
    base_td = create_thing_without_server(BaseCamera).thing_description()
    base_actions = set(base_td.actions.keys())
    base_props = set(base_td.properties.keys())

    sim_camera = create_thing_without_server(SimulatedCamera)
    sim_description = _get_clean_camera_description(sim_camera)
    opencv_camera = create_thing_without_server(OpenCVCamera)
    opencv_description = _get_clean_camera_description(opencv_camera)
    picamera_description = _get_clean_camera_description(mock_picam_thing)

    # Note. These are the actions and properties that are not exposed to the UI via
    # `primary_calibration_actions`, `secondary_calibration_actions`, or
    # `manual_camera_settings`.
    sim_actions = sim_description["actions"]
    sim_props = sim_description["properties"]

    opencv_actions = opencv_description["actions"]
    opencv_props = opencv_description["properties"]

    picamera_actions = picamera_description["actions"]
    picamera_props = picamera_description["properties"]

    # Camera actions and properties should generally be equivalent except for exposed
    # manual settings and calibration actions.
    assert opencv_actions == sim_actions == base_actions
    assert opencv_props == sim_props == base_props

    # For now PiCamera has a number of extra actions and properties. These should be
    # reduced over time by creating a way to use the functionality in a way as clearly
    # defined as PiCamera specific, or by replicating the functionality for other
    # cameras.
    picamera_extra_actions = {
        "set_static_green_equalisation",
        "set_ce_enable_to_off",
        "stop_streaming",
        "reset_ccm",
    }
    picamera_extra_props = {
        "mjpeg_bitrate",
        "colour_correction_matrix",
        "lens_shading_tables",
        "sensor_resolution",
        "capture_metadata",
        "camera_configuration",
        "stream_resolution",
        "tuning",
        "sensor_modes",
        "sensor_mode",
    }
    # Note these are only the action not exposed as calibration actions.
    for action in picamera_extra_actions:
        assert action in picamera_actions
    for props in picamera_extra_props:
        assert props in picamera_props
    assert picamera_actions - base_actions == picamera_extra_actions
    assert picamera_props - base_props == picamera_extra_props
