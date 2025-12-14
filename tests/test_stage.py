"""Test the stage without creating a full HTTP server and socket connection."""

import itertools
import tempfile

import pytest
from fastapi.testclient import TestClient
from httpx import HTTPStatusError
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import labthings_fastapi as lt
from labthings_fastapi.exceptions import NotConnectedToServerError

from openflexure_microscope_server.things.stage import (
    BaseStage,
    RedefinedBaseMovementError,
)
from openflexure_microscope_server.things.stage.dummy import DummyStage

from .mock_things.mock_cancel import MockCancel

# Keep the size and number of moves fairly small or the tests can take forever
point3d = st.tuples(
    st.integers(min_value=-100, max_value=100),
    st.integers(min_value=-100, max_value=100),
    st.integers(min_value=-100, max_value=100),
)

path3d = st.lists(point3d, min_size=5, max_size=10)


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
        @lt.action
        def move_relative(
            self,
            cancel: lt.deps.CancelHook,
            block_cancellation: bool = False,
            **kwargs: int,
        ):
            pass

    with pytest.raises(RedefinedBaseMovementError):
        BadStage1()

    class BadStage2(BaseStage):
        @lt.action
        def move_absolute(
            self,
            cancel: lt.deps.CancelHook,
            block_cancellation: bool = False,
            **kwargs: int,
        ):
            pass

    with pytest.raises(RedefinedBaseMovementError):
        BadStage2()


def _set_axis_direction(dummy_stage, direction):
    """Set the axis direction directly even if not connected to server."""
    try:
        dummy_stage.axis_inverted = direction
    except NotConnectedToServerError:
        pass


def test_apply_axis_direction_all_pos(dummy_stage):
    """Test the apply axis direction function behaves as expected when axis +v3."""
    # Directly create a stage not through a ThingServer to access private methods
    _set_axis_direction(dummy_stage, {"x": False, "y": False, "z": False})

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
    _set_axis_direction(dummy_stage, {"x": True, "y": False, "z": True})

    # A list of (input position, output position) to try
    position_pairs = [
        ([1, 2, 3], [-1, 2, -3]),  # list
        ([1, "2", "3"], [-1, 2, -3]),  # list with strings
        ((1, 2, 0), [-1, 2, 0]),  # tuple (gets converted to list)
        ({"x": 1, "y": 2, "z": 3}, {"x": -1, "y": 2, "z": -3}),  # mapping
        ({"x": 1, "z": 2, "y": 3}, {"x": -1, "z": -2, "y": 3}),  # mapping out of order
        ({"x": 1, "y": "2", "z": "3"}, {"x": -1, "y": 2, "z": -3}),  # mapping w strings
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
    assert stage_client.axis_inverted == {"x": True, "y": False, "z": False}
    # And check the thing state
    assert dummy_stage.thing_state == {"position": {"x": 0, "y": 0, "z": 0}}


def test_direction_inversion(stage_client, dummy_stage):
    """Check axes invert as expected when called."""
    # Can't set an arbitrary value via a client as read only:
    with pytest.raises(HTTPStatusError) as excinfo:
        stage_client.axis_inverted = {"x": 2, "y": 1, "z": 1}
    # Read only should set a 405 error code
    assert excinfo.value.response.status_code == 405
    # And not modify th initial value
    assert stage_client.axis_inverted == {"x": True, "y": False, "z": False}
    stage_client.invert_axis_direction(axis="x")
    assert stage_client.axis_inverted == {"x": False, "y": False, "z": False}
    stage_client.invert_axis_direction(axis="x")
    assert stage_client.axis_inverted == {"x": True, "y": False, "z": False}
    stage_client.invert_axis_direction(axis="y")
    assert stage_client.axis_inverted == {"x": True, "y": True, "z": False}
    stage_client.invert_axis_direction(axis="y")
    assert stage_client.axis_inverted == {"x": True, "y": False, "z": False}
    stage_client.invert_axis_direction(axis="z")
    assert stage_client.axis_inverted == {"x": True, "y": False, "z": True}
    stage_client.invert_axis_direction(axis="z")
    assert stage_client.axis_inverted == {"x": True, "y": False, "z": False}

    # Should error if axis doesn't exist, this is a KeyError in the server
    with pytest.raises(KeyError):
        dummy_stage.invert_axis_direction(axis="theta")
    # But a 422 over HTTP
    with pytest.raises(HTTPStatusError) as excinfo:
        stage_client.invert_axis_direction(axis="theta")
    assert excinfo.value.response.status_code == 422


def _test_move_relative(dummy_stage, axis_inverted, path):
    """Test moving relative, ensuring position and hardware position behave as expected.

    :param axis_inverted: Is used to set the inversion.
    :param path: The 3d path to move over, generated by hypothesis.
    """
    cancel = MockCancel()
    _set_axis_direction(dummy_stage, axis_inverted)
    # Explicitly do axes calculation here to check logic in main code.
    x_dir = -1 if axis_inverted["x"] else 1
    y_dir = -1 if axis_inverted["y"] else 1
    z_dir = -1 if axis_inverted["z"] else 1

    position = list(dummy_stage.position.values())
    for movement in path:
        dummy_stage.move_relative(
            cancel=cancel, x=movement[0], y=movement[1], z=movement[2]
        )
        position = [pos + move for pos, move in zip(position, movement, strict=True)]
        stage_pos = dummy_stage.get_xyz_position()
        hw_pos = dummy_stage._hardware_position
        assert position[0] == stage_pos[0] == hw_pos["x"] * x_dir
        assert position[1] == stage_pos[1] == hw_pos["y"] * y_dir
        assert position[2] == stage_pos[2] == hw_pos["z"] * z_dir


@given(path=path3d)
@settings(
    max_examples=3,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=10000,
)
def test_move_relative(stage_client, dummy_stage, path):
    """Loop over different inversion options and check that the stage moves as expected.

    3 paths are tried for each case of axis inversion. This checks both that the
    reported position changes as is input in path, and that the hardware position is
    inverted when appropriate.

    NOTE: it is essential that `stage_client` is imported even if any time it is used
    dummy stage could be used. This is because the fixture that creates stage client
    handles adding the dummy_stage to a server. It needs to have been added to a
    server for it not to throw errors about not being connected to a server.
    """
    # Note that the fixture is not reset. This is fine, because the stage_should work
    # no matter the starting position.

    axis_names = stage_client.axis_names
    # Create every combination of True/False for x,y,z.
    inversion_combinations = [
        dict(zip(axis_names, inverted, strict=True))
        for inverted in itertools.product([True, False], repeat=len(axis_names))
    ]
    print(path)
    for axis_inverted in inversion_combinations:
        _test_move_relative(
            dummy_stage=dummy_stage,
            axis_inverted=axis_inverted,
            path=path,
        )


def _test_move_absolute(dummy_stage, axis_inverted, path):
    """Test moving relative, ensuring position and hardware position behave as expected.

    :param axis_inverted: Is used to set the inversion.
    :param path: The 3d path to move over, generated by hypothesis.
    """
    cancel = MockCancel()
    _set_axis_direction(dummy_stage, axis_inverted)
    # Explicitly do axes calculation here to check logic in main code.
    x_dir = -1 if axis_inverted["x"] else 1
    y_dir = -1 if axis_inverted["y"] else 1
    z_dir = -1 if axis_inverted["z"] else 1
    position = list(dummy_stage.position.values())
    for move_to in path:
        dummy_stage.move_absolute(
            cancel=cancel, x=move_to[0], y=move_to[1], z=move_to[2]
        )
        position = move_to
        stage_pos = dummy_stage.get_xyz_position()
        hw_pos = dummy_stage._hardware_position
        assert position[0] == stage_pos[0] == hw_pos["x"] * x_dir
        assert position[1] == stage_pos[1] == hw_pos["y"] * y_dir
        assert position[2] == stage_pos[2] == hw_pos["z"] * z_dir


@given(path=path3d)
@settings(
    max_examples=3,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=10000,
)
def test_move_absolute(stage_client, dummy_stage, path):
    """Loop over different inversion options and check that the stage moves as expected.

    3 paths are tried for each case of axis inversion. This checks both that the
    reported position changes as is input in path, and that the hardware position is
    inverted when appropriate.

    NOTE: it is essential that `stage_client` is imported even if any time it is used
    dummy stage could be used. This is because the fixture that creates stage client
    handles adding the dummy_stage to a server. It needs to have been added to a
    server for it not to throw errors about not being connected to a server.
    """
    # Note that the fixture is not reset. This is fine, because the stage_should work
    # no matter the starting position.

    axis_names = stage_client.axis_names
    # Create every combination of True/False for x,y,z.
    inversion_combinations = [
        dict(zip(axis_names, inverted, strict=True))
        for inverted in itertools.product([True, False], repeat=len(axis_names))
    ]
    for axis_inverted in inversion_combinations:
        _test_move_absolute(
            dummy_stage=dummy_stage,
            axis_inverted=axis_inverted,
            path=path,
        )


def test_thing_description_equivalence(dummy_stage, mocker):
    """Stop extra actions getting added to child classes without explicit approval.

    To add an extra action to a stage this test needs to be updated, highlighting it at
    review. This tests should explain why the action isn't on the general base class.
    """
    mock_sangaboard = mocker.Mock()
    mocker.patch.dict("sys.modules", {"sangaboard": mock_sangaboard})
    from openflexure_microscope_server.things.stage.sangaboard import SangaboardThing

    # Flash LED isn't a standard stage action, most stages do not control illumination.
    extra_sanga_actions = ["flash_led"]

    base_td = BaseStage().thing_description()
    base_actions = set(base_td.actions.keys())
    base_properties = set(base_td.properties.keys())

    dummy_td = dummy_stage.thing_description()
    dummy_actions = set(dummy_td.actions.keys())
    dummy_properties = set(dummy_td.properties.keys())

    sanga_td = SangaboardThing().thing_description()
    # Remove known extra actions
    sanga_actions = list(sanga_td.actions.keys())
    for action in extra_sanga_actions:
        index = sanga_actions.index(action)
        sanga_actions.pop(index)
    sanga_actions = set(sanga_actions)
    sanga_properties = set(sanga_td.properties.keys())

    assert sanga_actions == dummy_actions == base_actions
    assert sanga_properties == dummy_properties == base_properties
