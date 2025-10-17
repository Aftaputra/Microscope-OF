"""File contains unit tests for stage_measure."""

from copy import copy
import logging
import pytest
from openflexure_microscope_server.things import stage_measure

LOGGER = logging.getLogger("mock-invocation_logger")


@pytest.fixture
def csm_matrix():
    """Return an example CSM matrix."""
    return [
        [0.03061156624485296, 1.8031242270940833],
        [1.773236372778601, 0.006660431608601435],
    ]


@pytest.fixture
def example_rom_data():
    """Return some example data in a RomDataTracker."""
    mock_positions = [
        {"x": 0, "y": 0, "z": 42},
        {"x": 727, "y": 2, "z": 154},
        {"x": 1454, "y": 4, "z": 228},
        {"x": 2181, "y": 6, "z": 351},
        {"x": 2908, "y": 8, "z": 509},
        {"x": 3635, "y": 10, "z": 617},
    ]
    rom_data = stage_measure.RomDataTracker()

    # loop through mock positions recording them with an offset.
    for position in mock_positions:
        offset = {"x": 54.4, "y": 0}
        rom_data.record_movement(position, offset)
    return rom_data


def test_predict_z(csm_matrix, example_rom_data):
    """Check that the prediction for the next z position is correct."""
    mock_z_diff = example_rom_data.predict_z_displacement(
        movement={"x": 2908, "y": 0},
        stage_position={"x": 3635, "y": 10, "z": 617},
        csm_matrix=csm_matrix,
    )
    expected_z_diff = 1343
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


@pytest.mark.parametrize(
    ("par_fraction", "should_error"),
    [
        (-0.20, True),
        (-0.11, True),
        (-0.09, False),
        (-0.05, False),
        (0.00, False),
        (0.05, False),
        (0.09, False),
        (0.11, True),
        (0.20, True),
    ],
)
def test_parasitic_detect(par_fraction, should_error):
    """Check error is raised if the fraction of parastitic motion is too high."""
    movement = {"x": 2908, "y": 0}

    offset = copy(movement)
    offset["y"] = movement["x"] * par_fraction
    if should_error:
        with pytest.raises(stage_measure.ParasiticMotionError):
            stage_measure._detect_parasitic_motion(movement=movement, offset=offset)
    else:
        # Nothing to check here as the only job of _detect_parasitic_motion is to
        # error if there is too much motion
        stage_measure._detect_parasitic_motion(movement=movement, offset=offset)


@pytest.fixture
def rom_thing(example_rom_data) -> stage_measure.RangeofMotionThing:
    """Return a RangeofMotionThing already populated with some example rom_data."""
    rom_thing = stage_measure.RangeofMotionThing()
    rom_thing._stream_resolution = [800, 600]
    rom_thing._rom_data = example_rom_data
    return rom_thing


@pytest.fixture
def mock_rom_deps(csm_matrix, mocker) -> stage_measure.RomDeps:
    """Return a RomDeps object full of mocks, except the logger which is LOGGER."""
    mock_csm = mocker.Mock()
    # Set up mock csm to return a CSM matrix
    mock_csm.image_to_stage_displacement_matrix = csm_matrix

    return stage_measure.RomDeps(
        autofocus=mocker.Mock(),
        stage=mocker.Mock(),
        cam=mocker.Mock(),
        csm=mock_csm,
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


@pytest.mark.parametrize(
    ("good_moves", "expected_to_detect_motion", "offset_calls"),
    [
        ([0, 1, 2], True, 3),  # First 3 pass all good
        ([1, 2, 3], True, 4),  # First is bad, will refocus, still complete
        ([2, 3, 4], True, 5),  # First 2 are bad, will refocus twice, still complete
        ([3, 4, 5], True, 6),  # First 3 are bad, will refocus 3 times, still complete
        ([4, 5, 6], False, 4),  # First 4 are bad, fails
        # Check second and 3rd measurement can fail after first fails 3 times
        ([3, 5, 7], True, 8),
        ([3, 6, 9], True, 10),
        ([3, 7, 11], True, 12),
        # But they can't fail 4 times
        ([3, 8, 9], False, 8),
        ([3, 7, 12], False, 12),
    ],
)
def test_stage_still_moves(
    good_moves,
    expected_to_detect_motion,
    offset_calls,
    rom_thing,
    mock_rom_deps,
    mocker,
):
    """Test _stage_still_moves correctly detects stage movement."""
    min_offset = 800 * stage_measure.SMALL_STEP / 100 * stage_measure.DETECT_MOTION_TOL

    def gen_offsets(*_args, **_kwargs):
        """Generate offset dictionaries with small moves unless count matches ``good_moves``."""
        i = 0
        while True:
            x = min_offset * 1.2 if i in good_moves else 0.1
            yield {"x": x, "y": 0}
            i += 1

    mock_offset_from = mocker.patch.object(
        rom_thing, "_offset_from", side_effect=gen_offsets()
    )

    still_moves = rom_thing._stage_still_moves(
        axis="x",
        direction=1,
        rom_deps=mock_rom_deps,
    )
    assert still_moves is expected_to_detect_motion
    assert mock_offset_from.call_count == offset_calls


def test_big_z_corrected_movement(rom_thing, mock_rom_deps):
    """Check big z corrected move moves in x/y and z the expected distances."""
    mock_rom_deps.stage.position = {"x": 5000, "y": 30, "z": 500}

    rom_thing._big_z_corrected_movement("x", direction=1, rom_deps=mock_rom_deps)

    expected_movement = {"x": 800 * stage_measure.BIG_STEP / 100, "y": 0}

    # Check there is one z move in steps
    assert mock_rom_deps.stage.move_relative.call_count == 1
    move_kwargs = mock_rom_deps.stage.move_relative.call_args.kwargs
    assert "x" not in move_kwargs
    assert "y" not in move_kwargs
    assert "z" in move_kwargs
    move_kwargs["z"] = 1162

    # And one move in image coordinates
    assert mock_rom_deps.csm.move_in_image_coordinates.call_count == 1
    lat_mov_kwargs = mock_rom_deps.csm.move_in_image_coordinates.call_args.kwargs
    assert lat_mov_kwargs == expected_movement
