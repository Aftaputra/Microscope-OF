"""Tests for the autofoucs logic.

This doesn't check the behaviour of the JPEG shaprness monitor.
"""

import numpy as np
import pytest

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things.autofocus import (
    AutofocusThing,
    NoFocusFoundError,
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
