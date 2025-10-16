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
