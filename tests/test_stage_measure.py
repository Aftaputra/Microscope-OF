"""File contains unit tests for stage_measure."""

import logging
import pytest
from openflexure_microscope_server.things import stage_measure

LOGGER = logging.getLogger("mock-invocation_logger")


def test_predict_z():
    """Check that the prediction for the next z position is correct."""
    mock_positions = [
        {"x": 0, "y": 0, "z": 42},
        {"x": 727, "y": 2, "z": 154},
        {"x": 1454, "y": 4, "z": 228},
        {"x": 2181, "y": 6, "z": 351},
        {"x": 2908, "y": 8, "z": 509},
        {"x": 3635, "y": 10, "z": 617},
    ]
    rom_data = stage_measure.RomDataTracker()

    for position in mock_positions:
        offset = {"x": 54.4, "y": 0}
        rom_data.record_movement(position, offset)

    csm_matrix = [
        [0.03061156624485296, 1.8031242270940833],
        [1.773236372778601, 0.006660431608601435],
    ]

    mock_z_diff = rom_data.predict_z_displacament(
        movement={"x": 2908, "y": 0},
        stage_position={"x": 3635, "y": 10, "z": 617},
        csm_matrix=csm_matrix,
    )
    expected_z_diff = 1343.1625053206606
    assert mock_z_diff == expected_z_diff


@pytest.mark.parametrize(
    ("movement", "axis", "other_axis"),
    [
        ({"x": 2908, "y": 0}, "x", "y"),
        ({"x": -29, "y": 0}, "x", "y"),
        ({"x": 0, "y": 123}, "y", "x"),
        ({"x": 0, "y": -456}, "y", "x"),
    ],
)
def test_axis_from_movement_dict(movement, axis, other_axis):
    """Test that _axis_from_movement_dict identifies the correct axes."""
    assert stage_measure._axis_from_movement_dict(movement) == axis

    ret_axes = stage_measure._axis_from_movement_dict(movement, return_other=True)
    assert ret_axes == (axis, other_axis)


@pytest.mark.parametrize("movement", [{"x": 0, "y": 0}, {"x": 10, "y": 10}])
def test_error_on_axis_from_movement_dict(movement):
    """Check _axis_from_movement_dict errors if both axes are zero, or both are non-zero."""
    with pytest.raises(ValueError, match="Either x or y movement should be zero"):
        assert stage_measure._axis_from_movement_dict(movement)


def test_parasitic_detect():
    """Check that the parasitic error is raised correctly."""
    with pytest.raises(stage_measure.ParasiticMotionError):
        stage_measure._detect_parasitic_motion(
            movement={"x": 2908, "y": 0}, offset={"x": 2908, "y": 300}
        )


@pytest.fixture
def rom_thing() -> stage_measure.RangeofMotionThing:
    """Return a RangeofMotionThing."""
    return stage_measure.RangeofMotionThing()


@pytest.fixture
def mock_rom_deps(mocker) -> stage_measure.RomDeps:
    """Return a RomDeps object full of mocks, except the logger which is LOGGER."""
    return stage_measure.RomDeps(
        autofocus=mocker.Mock(),
        stage=mocker.Mock(),
        cam=mocker.Mock(),
        csm=mocker.Mock(),
        logger=LOGGER,
    )


def test_offset_from(rom_thing, mock_rom_deps, mocker):
    """Check the calls and returns for RangeofMotionThing._offset_from."""
    # Set up mock for the FFT displacement
    disp_between_route = (
        "openflexure_microscope_server.things.stage_measure."
        "fft_image_tracking.displacement_between_images"
    )
    mock_disp_between = mocker.patch(
        disp_between_route,
        side_effect=([123, 456],),
    )

    # Run it
    offset = rom_thing._offset_from(before_img="MOCK_IMAGE", rom_deps=mock_rom_deps)

    # Check the offset is a dictionary with the correct values for the axes
    assert offset["x"] == 456
    assert offset["y"] == 123
    # Check 1 image was taken
    assert mock_rom_deps.cam.grab_as_array.call_count == 1
    mock_after_image = mock_rom_deps.cam.grab_as_array.return_value
    # Check the FFT displacement was called once
    assert mock_disp_between.call_count == 1
    displacement_kwargs = mock_disp_between.call_args.kwargs
    # Check the image inputs
    assert displacement_kwargs["image_0"] == "MOCK_IMAGE"
    assert displacement_kwargs["image_1"] == mock_after_image


@pytest.mark.parametrize("perform_autofocus", [True, False])
def test_move_and_measure(perform_autofocus, rom_thing, mock_rom_deps, mocker):
    """Test _move_and_measure with and without initial autofocus checking call counts.

    This doesn't test with the repeate autofocus if motion isn't detected
    """
    mock_offset_value = {"x": 100, "y": 3}
    mocker.patch.object(rom_thing, "_offset_from", side_effect=(mock_offset_value,))
    movement = {"x": 100, "y": 0}
    offset = rom_thing._move_and_measure(
        movement=movement, rom_deps=mock_rom_deps, perform_autofocus=perform_autofocus
    )

    # Check exactly 1 move
    assert mock_rom_deps.csm.move_in_image_coordinates.call_count == 1
    # The kwargs of the call should movement dict
    assert mock_rom_deps.csm.move_in_image_coordinates.call_args.kwargs == movement
    # Check autofocus call count
    expected_af_count = 1 if perform_autofocus else 0
    assert mock_rom_deps.autofocus.looping_autofocus.call_count == expected_af_count
    # And check final return
    assert offset == mock_offset_value


@pytest.mark.parametrize(
    ("x_offsets", "n_offset_measures", "expected_return"),
    [
        ([5.1, 0.2], 1, {"x": 5.1, "y": 0}),
        ([-5.1, 0.2], 1, {"x": -5.1, "y": 0}),
        ([0.1, 5.2, 0.3, 0.4, 0.5], 2, {"x": 5.2, "y": 0}),
        ([0.1, 0.2, 5.3, 0.4, 0.5], 3, {"x": 5.3, "y": 0}),
        ([0.1, 0.2, 0.3, 5.4, 0.5], 4, {"x": 5.4, "y": 0}),
        # n_offset_measures shouldn't go higher than 4 as max autofocus repeats is 3
        ([0.1, 0.2, 0.3, 0.4, 5.5], 4, {"x": 0.4, "y": 0}),
    ],
)
def test_move_and_measure_with_refocus(
    x_offsets, n_offset_measures, expected_return, rom_thing, mock_rom_deps, mocker
):
    """Test _move_and_measure with final refocus if offset is too small."""
    return_dicts = tuple({"x": x, "y": 0} for x in x_offsets)
    offset_from_mock = mocker.patch.object(
        rom_thing, "_offset_from", side_effect=return_dicts
    )
    movement = {"x": 10, "y": 0}
    offset = rom_thing._move_and_measure(
        movement=movement,
        rom_deps=mock_rom_deps,
        perform_autofocus=False,
        max_autofocus_repeats=3,
        abs_min_offset=5,
    )
    # Check exactly 1 move
    assert mock_rom_deps.csm.move_in_image_coordinates.call_count == 1
    # Check expected _offset_from calls
    assert offset_from_mock.call_count == n_offset_measures
    # The kwargs of the call should movement dict
    assert mock_rom_deps.csm.move_in_image_coordinates.call_args.kwargs == movement
    # Check autofocus call count is 1 less than number of offset measures as no autofocus
    # is performed before the first one
    expected_af_count = n_offset_measures - 1
    assert mock_rom_deps.autofocus.looping_autofocus.call_count == expected_af_count
    # And check final return
    assert offset == expected_return


def test_move_back_until_motion_detected(rom_thing, mock_rom_deps, mocker):
    """Check that _move_back_until_motion_detected is making increasing negative moves.

    The moves for this method should be in opposite direction to the direction
    specified as this is moving back after the stage reaches end of its movement.
    """

    def gen_offset(*_args, **_kwargs):
        return {"x": 0, "y": 0}

    mock_move_n_meas = mocker.patch.object(
        rom_thing, "_move_and_measure", side_effect=gen_offset
    )

    with pytest.raises(RuntimeError, match="Cannot detect motion again"):
        rom_thing._move_back_until_motion_detected("y", -1, rom_deps=mock_rom_deps)
    assert mock_move_n_meas.call_count == 10
    for i, call_args in enumerate(mock_move_n_meas.call_args_list):
        call_args.kwargs["movement"] = {"x": 0, "y": 2**i}
        call_args.kwargs["perform_autofocus"] = False

    ## Reset mock and change the side effect
    mock_move_n_meas.reset_mock()
    mock_move_n_meas.side_effect = (
        {"x": 0, "y": 0},
        {"x": 0, "y": 0},
        {"x": 21, "y": 0},
    )

    # Other axis and direction this time
    rom_thing._move_back_until_motion_detected("x", 1, rom_deps=mock_rom_deps)

    # Should only be called 3 times
    assert mock_move_n_meas.call_count == 3
    for i, call_args in enumerate(mock_move_n_meas.call_args_list):
        call_args.kwargs["movement"] = {"x": -(2**i), "y": 0}
        call_args.kwargs["perform_autofocus"] = False
