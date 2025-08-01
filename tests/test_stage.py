"""Test the stage without creating a full HTTP server and socket connection."""

from collections.abc import Mapping
import tempfile

from fastapi.testclient import TestClient
import pytest
from httpx import HTTPStatusError

import labthings_fastapi as lt
from labthings_fastapi.exceptions import NotConnectedToServerError

from openflexure_microscope_server.things.stage import (
    BaseStage,
    RedefinedBaseMovementError,
)
from openflexure_microscope_server.things.stage.dummy import DummyStage


@pytest.fixture
def dummy_stage():
    """Return a dummy stage with a very low step time."""
    return DummyStage(step_time=0.000001)


@pytest.fixture
def thing_server(dummy_stage):
    """Yield a server with a very basic configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        server = lt.ThingServer(settings_folder=tmpdir)
        server.add_thing(dummy_stage, "/stage/")
        yield server


@pytest.fixture
def stage_client(thing_server):
    """Yield a labthings ThingClient for the stage."""
    with TestClient(thing_server.app) as test_client:
        yield lt.ThingClient.from_url("/stage/", client=test_client)


def test_override_base_movement():
    """Child classes of stage should implement functions in the hardware reference frame.

    ``move_absolute`` and ``move_relative`` are in the program reference frame and
    convert to the hardware frame. It is recommended to override
    ``_hardware_move_relative`` and ``_hardware_move_absolute`` instead.

    Check that the expected error is raised if the methods are overridden.
    """

    class BadStage1(BaseStage):
        @lt.thing_action
        def move_relative(
            self,
            cancel: lt.deps.CancelHook,
            block_cancellation: bool = False,
            **kwargs: Mapping[str, int],
        ):
            pass

    with pytest.raises(RedefinedBaseMovementError):
        BadStage1()

    class BadStage2(BaseStage):
        @lt.thing_action
        def move_absolute(
            self,
            cancel: lt.deps.CancelHook,
            block_cancellation: bool = False,
            **kwargs: Mapping[str, int],
        ):
            pass

    with pytest.raises(RedefinedBaseMovementError):
        BadStage2()


def _set_axis_direction(dummy_stage, direction):
    """Set the axis direction directly even if not connected to server."""
    try:
        dummy_stage.axis_direction = direction
    except NotConnectedToServerError:
        pass


def test_apply_axis_direction_all_pos(dummy_stage):
    """Test the apply axis direction function behaves as expected when axis +v3."""
    # Directly create a stage not through a ThingServer to access private methods
    _set_axis_direction(dummy_stage, {"x": 1, "y": 1, "z": 1})

    # A list of positions to try
    positions = [
        [1, 2, 3],  # list
        {"x": 1, "y": 2, "z": 3},  # mapping
        {"x": 1, "z": 2, "y": 3},  # mapping out of order
        {"x": 3},  # Mapping with only 1 value
        {"x": 1, "z": 2},  # Mapping with only 2 values
    ]
    for pos in positions:
        assert dummy_stage._apply_axis_direction(pos) == pos

    # Check tuple separately as it gets converted to list
    assert dummy_stage._apply_axis_direction((1, 2, 0)) == [1, 2, 0]


def test_apply_axis_direction_mixed(dummy_stage):
    """Test the apply axis direction function behaves as expected when axis dirs are mixed."""
    # Make x and z negative
    _set_axis_direction(dummy_stage, {"x": -1, "y": 1, "z": -1})

    # A list of (input position, output position) to try
    position_pairs = [
        ([1, 2, 3], [-1, 2, -3]),  # list
        ((1, 2, 0), [-1, 2, 0]),  # tuple (gets converted to list)
        ({"x": 1, "y": 2, "z": 3}, {"x": -1, "y": 2, "z": -3}),  # mapping
        ({"x": 1, "z": 2, "y": 3}, {"x": -1, "z": -2, "y": 3}),  # mapping out of order
        ({"x": 3}, {"x": -3}),  # Mapping with only 1 value
        ({"x": 1, "z": 2}, {"x": -1, "z": -2}),  # Mapping with only 2 values
    ]
    for pos, expected_pos in position_pairs:
        assert dummy_stage._apply_axis_direction(pos) == expected_pos


def test_apply_axis_errors(dummy_stage):
    """Test the apply axis direction returns appropriate errors."""
    with pytest.raises(TypeError):
        dummy_stage._apply_axis_direction(None)
    with pytest.raises(TypeError):
        dummy_stage._apply_axis_direction("Onwards!")
    with pytest.raises(KeyError):
        dummy_stage._apply_axis_direction({"x": -1, "y": 2, "z": 4, "up": -3})
    with pytest.raises(KeyError):
        dummy_stage._apply_axis_direction({"x": -1, "y": 2, "up": -3})


def test_default_values(stage_client, dummy_stage):
    """Check the default values for the dummy stage."""
    # axes are x, y, z (note that going through the thing, client the tuple is
    # converted to a list.
    assert stage_client.axis_names == ["x", "y", "z"]
    # position starts at 0, 0, 0
    assert stage_client.position == {"x": 0, "y": 0, "z": 0}
    # axis direction starts is -1, 1, 1 for the dummy stage
    assert stage_client.axis_direction == {"x": -1, "y": 1, "z": 1}
    # And check the thing state
    assert dummy_stage.thing_state == {"position": {"x": 0, "y": 0, "z": 0}}


def test_direction_inversion(stage_client):
    """Check axes invert as expected when called."""
    # Can't set an arbitrary value via a client as read only:
    with pytest.raises(HTTPStatusError) as excinfo:
        stage_client.axis_direction = {"x": 2, "y": 1, "z": 1}
    # Read only should set a 405 error code
    assert excinfo.value.response.status_code == 405
    # And not modify th initial value
    assert stage_client.axis_direction == {"x": -1, "y": 1, "z": 1}
    stage_client.invert_axis_direction(axis="x")
    assert stage_client.axis_direction == {"x": 1, "y": 1, "z": 1}
    stage_client.invert_axis_direction(axis="x")
    assert stage_client.axis_direction == {"x": -1, "y": 1, "z": 1}
    stage_client.invert_axis_direction(axis="y")
    assert stage_client.axis_direction == {"x": -1, "y": -1, "z": 1}
    stage_client.invert_axis_direction(axis="y")
    assert stage_client.axis_direction == {"x": -1, "y": 1, "z": 1}
    stage_client.invert_axis_direction(axis="z")
    assert stage_client.axis_direction == {"x": -1, "y": 1, "z": -1}
    stage_client.invert_axis_direction(axis="z")
    assert stage_client.axis_direction == {"x": -1, "y": 1, "z": 1}
