"""Tests for the autofoucs logic.

This doesn't check the behaviour of the JPEG shaprness monitor.
"""

import numpy as np
import pytest

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things.autofocus import (
    AutofocusThing,
    JPEGSharpnessMonitor,
    NoFocusFoundError,
    SharpnessMethod,
)


def fake_sharpness_data(
    dz: int, start_z: int, max_loc: int, length: int = 41
) -> tuple[list[float], np.ndarray, np.ndarray]:
    """Create some fake data for the shapeness.

    The highest returned sharpness is closest to max_loc
    """
    # Some fake timestamps
    times = [i / 10 + 100000 for i in range(length)]
    img_dz = dz / (length - 1)
    heights = [round(start_z + i * img_dz) for i in range(length)]
    # Sharpnesses fall off linearly in this model.
    sharpnesses = [10 * dz - abs(max_loc - h) for h in heights]
    return times, np.array(heights), np.array(sharpnesses)


@pytest.mark.parametrize(
    ("start_z", "max_loc", "centre", "attempts_expected", "passes"),
    [
        # To complete, the max must be in the central 1200, so -600 to 600 when looping
        # from -1000 to 1000
        (0, 550, True, 1, True),  # Found in loop1 from -1000 to 1000
        (0, 650, True, 2, True),  # Just outside the limit in loop1
        (0, 1300, True, 2, True),  # Found in loop2 from 0 to 2000
        (0, 1300, False, 1, True),  # Found in loop1 from 0 to 2000 (as start="base")
        (0, -1300, True, 2, True),  # Found in loop2 from 0 to 2000
        (0, 7300, True, 8, True),  # Found in loop8 from 6000 to 8000
        (0, 9300, True, 10, True),  # Found in loop10 from 8000 to 10000
        (0, 9900, True, 10, False),  # Still not central in loop 10, doesn't pass
    ],
)
def test_looping_autofocus(start_z, max_loc, centre, attempts_expected, passes, mocker):
    """Test the high level looping autofocus algorithm."""
    dz = 2000
    autofocus_thing = create_thing_without_server(AutofocusThing, mock_all_slots=True)

    # Make a mock stage where move_absolute abs and relative updates the position counter.
    autofocus_thing._stage.position = {"x": 0, "y": 0, "z": start_z}

    def set_pos(**kwargs: int) -> None:
        """Move absolute should update position. So make a side effect for the mock."""
        for axis, value in kwargs.items():
            autofocus_thing._stage.position[axis] = value

    def adjust_pos(**kwargs: int) -> None:
        """Move relative should update position. So make a side effect for the mock."""
        # Remove backlash compensation from the dict if it exists.
        kwargs.pop("backlash_compensation", None)
        for axis, value in kwargs.items():
            autofocus_thing._stage.position[axis] += value

    autofocus_thing._stage.move_absolute.side_effect = set_pos
    autofocus_thing._stage.move_relative.side_effect = adjust_pos

    # Make a mock sharpness monitor that can generate sharpness data.
    sharpness_monitor = mocker.MagicMock()
    sharpness_monitor.focus_rel.return_value = (0, 0)

    def return_sharpness(*_args) -> tuple[list[float], np.ndarray, np.ndarray]:
        """Generate sharpnesses based on parameterised input, and mock stage position."""
        return fake_sharpness_data(
            dz=dz,
            start_z=autofocus_thing._stage.position["z"],
            max_loc=max_loc,
        )

    sharpness_monitor.move_data.side_effect = return_sharpness

    # Mock the context manager call so out MagicMock sharpness monitor is returned.
    mock_context = mocker.patch(
        "openflexure_microscope_server.things.autofocus.JPEGSharpnessMonitor"
    )
    mock_context.return_value.__enter__.return_value = sharpness_monitor
    mock_context.return_value.__exit__.return_value = None

    if passes:
        autofocus_thing.looping_autofocus(dz=dz, start="centre" if centre else "base")
    else:
        with pytest.raises(NoFocusFoundError):
            autofocus_thing.looping_autofocus(
                dz=dz, start="centre" if centre else "base"
            )
    assert sharpness_monitor.focus_rel.call_count == attempts_expected
    assert abs(max_loc - autofocus_thing._stage.position["z"]) < dz / 40


@pytest.fixture
def mock_camera(mocker):
    """Mock a camera to return fom properties."""
    camera = mocker.MagicMock()
    camera.supports_focus_fom = True
    camera.focus_fom = 123
    return camera


@pytest.fixture
def mock_stage(mocker):
    """Mock a stage to return position."""
    stage = mocker.MagicMock()
    stage.position = {"x": 0, "y": 0, "z": 0}
    return stage


def test_record_defaults_to_method(mock_stage, mock_camera):
    """If record=None, only the selected method is recorded."""
    monitor = JPEGSharpnessMonitor(
        mock_stage,
        mock_camera,
        method=SharpnessMethod.FOCUS_FOM,
    )

    assert monitor.record == SharpnessMethod.FOCUS_FOM


def test_zero_record_defaults_to_method(mock_stage, mock_camera):
    """If record=0, only the selected method is recorded."""
    monitor = JPEGSharpnessMonitor(
        mock_stage,
        mock_camera,
        method=SharpnessMethod.FOCUS_FOM,
        record=0,
    )

    assert monitor.record == SharpnessMethod.FOCUS_FOM


def test_record_must_include_selected_method(mock_stage, mock_camera):
    """The selected autofocus metric must also be recorded."""
    with pytest.raises(ValueError, match="not being recorded"):
        JPEGSharpnessMonitor(
            mock_stage,
            mock_camera,
            method=SharpnessMethod.FOCUS_FOM,
            record=SharpnessMethod.JPEG,
        )


def test_focus_fom_requires_camera_support(mock_stage, mock_camera):
    """FocusFoM recording requires camera support."""
    mock_camera.supports_focus_fom = False

    with pytest.raises(ValueError, match="doesn't support"):
        JPEGSharpnessMonitor(
            mock_stage,
            mock_camera,
            method=SharpnessMethod.FOCUS_FOM,
        )


def test_jpeg_sizes_property_requires_recording(mock_stage, mock_camera):
    """JPEG sizes should error if JPEG recording disabled."""
    monitor = JPEGSharpnessMonitor(
        mock_stage,
        mock_camera,
        method=SharpnessMethod.FOCUS_FOM,
    )

    with pytest.raises(ValueError, match="JPEG sizes are not being recorded"):
        _ = monitor.jpeg_sizes


def test_focus_fom_property_requires_recording(mock_stage, mock_camera):
    """FocusFoM values should error if FOM recording disabled."""
    monitor = JPEGSharpnessMonitor(
        mock_stage,
        mock_camera,
        method=SharpnessMethod.JPEG,
    )

    with pytest.raises(ValueError, match="FocusFoM values are not being recorded"):
        _ = monitor.focus_foms


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        (SharpnessMethod.JPEG, [100, 200, 300]),
        (SharpnessMethod.FOCUS_FOM, [1, 5, 2]),
    ],
)
def test_move_data_uses_selected_method(
    method,
    expected,
    mock_stage,
    mock_camera,
):
    """move_data should select the correct sharpness metric."""
    monitor = JPEGSharpnessMonitor(
        mock_stage,
        mock_camera,
        method=method,
        record=SharpnessMethod.JPEG + SharpnessMethod.FOCUS_FOM,
    )

    monitor._jpeg_times = [1.0, 2.0, 3.0]
    monitor._jpeg_sizes = [100, 200, 300]
    monitor._focus_foms = [1, 5, 2]

    monitor._stage_times = [0.5, 3.5]
    monitor._stage_positions = [
        {"z": 0},
        {"z": 100},
    ]

    _, _, sharpnesses = monitor.move_data(0)

    assert sharpnesses.tolist() == expected


def test_monitor_records_both_metrics(mock_stage, mock_camera):
    """Both JPEG and FocusFoM metrics can be recorded together."""
    monitor = JPEGSharpnessMonitor(
        mock_stage,
        mock_camera,
        method=SharpnessMethod.JPEG,
        record=SharpnessMethod.JPEG + SharpnessMethod.FOCUS_FOM,
    )

    monitor._jpeg_sizes.append(999)
    monitor._focus_foms.append(321)

    assert monitor.jpeg_sizes == [999]
    assert monitor.focus_foms == [321]


def test_move_data_uses_focus_fom(mock_stage, mock_camera):
    """Test that move_data returns the chosen metric."""
    monitor = JPEGSharpnessMonitor(
        mock_stage,
        mock_camera,
        method=SharpnessMethod.FOCUS_FOM,
        record=SharpnessMethod.JPEG + SharpnessMethod.FOCUS_FOM,
    )

    # Record both sharpness metrics
    monitor._jpeg_times = [1.0, 2.0, 3.0]
    monitor._jpeg_sizes = [100, 200, 300]
    monitor._focus_foms = [10, 99, 20]

    monitor._stage_times = [0.5, 3.5]
    monitor._stage_positions = [
        {"z": 0},
        {"z": 100},
    ]

    # sharpnesses chosen by the chosen method
    _, _, sharpnesses = monitor.move_data(0)

    # ensure sharpnesses matches focus_foms
    assert sharpnesses.tolist() == [10, 99, 20]
