"""Tests for the Illumination thing."""

import pytest

from labthings_fastapi.testing import create_thing_without_server

from openflexure_microscope_server.things.illumination import (
    Illumination,
    SangaIllumination,
    SimulatorIllumination,
)


def test_base_illumination_flash_not_implemented():
    """Check that calling flash on the base Illumination raises NotImplementedError."""
    ill = create_thing_without_server(Illumination)
    with pytest.raises(NotImplementedError, match="Flashing the LED can only be done"):
        ill.flash(number_of_flashes=1, dt=0.01)


@pytest.fixture
def sanga_mock_stage():
    """Return a SangaIllumination with a mocked stage."""
    return create_thing_without_server(SangaIllumination, mock_all_slots=True)


@pytest.fixture
def sim_mock_cam():
    """Return a SimulatorIllumination with a mocked camera."""
    return create_thing_without_server(SimulatorIllumination, mock_all_slots=True)


def test_sanga_flash_calls_led(sanga_mock_stage):
    """Test that flashing calls set_led with correct parameters."""
    number_of_flashes = 3
    dt = 0.01  # tiny sleep for test speed

    sanga_mock_stage.flash(number_of_flashes=number_of_flashes, dt=dt)

    # Each flash calls set_led False then True
    assert sanga_mock_stage._stage.set_led.call_count == 2 * number_of_flashes

    # Check that False and True are alternating when sent to _stage.set_led
    calls = sanga_mock_stage._stage.set_led.call_args_list
    expected_sequence = [False, True] * number_of_flashes
    for call, expected in zip(calls, expected_sequence, strict=True):
        args, kwargs = call
        assert args[0] == expected


def test_sim_flash_calls_led(sim_mock_cam):
    """Test that simulator flash calls set_led correctly."""
    number_of_flashes = 2
    dt = 0.01

    sim_mock_cam.flash(number_of_flashes=number_of_flashes, dt=dt)

    # Each flash calls set_led False then True
    assert sim_mock_cam._cam.set_led.call_count == 2 * number_of_flashes

    # Check that False and True are alternating when sent to _cam.set_led
    calls = sim_mock_cam._cam.set_led.call_args_list
    expected_sequence = [False, True] * number_of_flashes
    for call, expected in zip(calls, expected_sequence, strict=True):
        args, kwargs = call
        assert args[0] == expected
