"""Test the functionality specific to the simulated camera."""

import logging

import pytest
from hypothesis import given
from hypothesis import strategies as st

import labthings_fastapi as lt

from openflexure_microscope_server.things.camera import simulation
from openflexure_microscope_server.things.camera.simulation import SimulatedCamera
from openflexure_microscope_server.things.stage.dummy import DummyStage

from ..shared_utils.lt_test_utils import LabThingsTestEnv


@pytest.fixture
def test_env() -> lt.ThingClient:
    """Yield a test environment with the Simulated Camera and Dummy Stage."""
    thing_conf = {"camera": SimulatedCamera, "stage": DummyStage}
    with LabThingsTestEnv(things=thing_conf) as env:
        yield env


def test_downsample_shape_2d():
    """Test downsampling for 2D array."""
    shape_2d = (100, 80)
    result_2d = simulation._downsample_shape(shape_2d)
    assert len(result_2d) == 2
    assert result_2d == (100 // simulation.DOWNSAMPLE, 80 // simulation.DOWNSAMPLE)


def test_downsample_shape_3d():
    """Test downsampling for 3D array, should not affect 3rd axis or shape."""
    shape_3d = (120, 60, 3)
    result_3d = simulation._downsample_shape(shape_3d)
    assert len(result_3d) == 3
    assert result_3d == (120 // simulation.DOWNSAMPLE, 60 // simulation.DOWNSAMPLE, 3)


def test_downsample_shape_invalid_length():
    """Shapes that are not length 2 or 3 should raise ValueError."""
    with pytest.raises(ValueError, match="Shape should be a 2 or 3 element tuple."):
        simulation._downsample_shape((1,))

    with pytest.raises(ValueError, match="Shape should be a 2 or 3 element tuple."):
        simulation._downsample_shape((1, 2, 3, 4))


def all_colours_present(
    col_str: str, colours: list[tuple[int, int, int]], tries: int = 100
) -> bool:
    """Check that for a given colour string that all listed colours are returned.

    A helper function for testing simulation.colour_str_to_colour. As the result is
    randomised the test just tries multiple times. In theory could fail, so pick
    tries high enough if there are lots of colours in col_str.
    """
    found = [False for _c in colours]
    for _i in range(tries):
        col_tuple = simulation.colour_str_to_colour(col_str)
        if col_tuple not in colours:
            raise ValueError("Unexpected colour returned.")
        found[colours.index(col_tuple)] = True
        # Don't exit early or we don't confrm that extra colours are not returned.
    return all(found)


def test_colour_str_to_colour():
    """Test colour_str_to_colour with some basic predefined test cases."""
    # A basic test
    assert simulation.colour_str_to_colour("#123456") == (0x12, 0x34, 0x56)
    # A basic test with a trailing semicolon and surrounding spacing
    assert simulation.colour_str_to_colour("  #123456 ; ") == (0x12, 0x34, 0x56)
    # A 2 colour test
    assert all_colours_present(
        "#123456; #654321", [(0x12, 0x34, 0x56), (0x65, 0x43, 0x21)]
    )
    # A failure_test (to check the helper function works!)
    with pytest.raises(ValueError, match="Unexpected colour returned."):
        assert all_colours_present(
            "#123456; #654321", [(0x12, 0x34, 0x56), (0x11, 0x11, 0x11)]
        )
    # And some incorrect strings that should fire an error in colour_str_to_colour
    bad_colours = ["foobar", "pink", "#123", "#123456, #654321"]
    for colour_str in bad_colours:
        with pytest.raises(
            ValueError, match=r".*not a valid colour. Please use HTML hex notation."
        ):
            simulation.colour_str_to_colour(colour_str)


@given(st.from_regex(simulation.COLOUR_LIST_REGEX, fullmatch=True))
def test_colour_list_regex(colour_str):
    """Check that anything matching the regex doesn't error when generating colours.

    This will error if colour_str when splot into individual colours produces
    # an incorrect colour. Trying 100 times for each colour_str as the returned colour
    is randomised. Hypothesis will try to create the strings that match the regex but
    break the test.
    """
    for _ in range(100):
        simulation.colour_str_to_colour(colour_str)


def test_canvas_regeneration(test_env, caplog):
    """Check canvas is regenerated if blob density of colour are changed."""
    camera = test_env.get_thing_by_type(SimulatedCamera)
    cached_canvas = camera.canvas
    original_colour = camera.colour

    # First try a bad colour string
    with caplog.at_level(logging.WARNING):
        camera.colour = "foobar"
    assert len(caplog.messages) == 1
    assert caplog.messages[0] == "foobar is not a valid colour string."
    # Value and canvas unchanged
    assert camera.colour == original_colour
    assert camera.canvas is cached_canvas

    # Set a valid colour
    camera.colour = "#123456"
    assert camera.colour == "#123456"
    # canvas updated
    assert camera.canvas is not cached_canvas

    # Cache again
    cached_canvas = camera.canvas
    camera.blob_density = 321
    assert camera.blob_density == 321
    # Canvas updated again
    assert camera.canvas is not cached_canvas


def test_simulation_cam_calibration(test_env):
    """Test that the simulated camera can be calibrated and reports calibration correctly."""
    camera = test_env.get_thing_by_type(SimulatedCamera)
    assert camera.calibration_required
    camera.full_auto_calibrate()
    assert not camera.calibration_required
    assert camera.background_detector_status.ready
