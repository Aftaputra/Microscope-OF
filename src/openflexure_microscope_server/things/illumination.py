"""A module to handle the illumination in LabThings."""

import time
from typing import Literal

import labthings_fastapi as lt

from .camera import BaseCamera
from .stage import BaseStage


class Illumination(lt.Thing):
    """Abstract illumination controller."""

    @lt.action
    def flash(
        self,
        number_of_flashes: int = 10,
        dt: float = 0.5,
    ) -> None:
        """Flash the illumination source."""
        raise NotImplementedError(
            "Flashing the LED can only be done from the simulator or sangaboard"
        )


class SangaIllumination(Illumination):
    """Illumination driven by a Sangaboard."""

    _stage: BaseStage = lt.thing_slot()

    @lt.action
    def flash(
        self,
        number_of_flashes: int = 10,
        dt: float = 0.5,
        led_channel: Literal["cc"] = "cc",
    ) -> None:
        """Flash an LED a given number of times.

        Flashes the LED on channel led_channel number_of_flashes times,
        for a duration of dt each.
        """
        for _ in range(number_of_flashes):
            self._stage.set_led(False, led_channel)
            time.sleep(dt)
            self._stage.set_led(True, led_channel)
            time.sleep(dt)


class SimulatorIllumination(Illumination):
    """Illumination control in the simulator."""

    _cam: BaseCamera = lt.thing_slot()

    @lt.action
    def flash(
        self,
        number_of_flashes: int = 10,
        dt: float = 0.5,
        led_channel: Literal["cc"] = "cc",
    ) -> None:
        """Flash an LED a given number of times.

        Flashes the LED on channel led_channel number_of_flashes times,
        for a duration of dt each.
        """
        for _ in range(number_of_flashes):
            self._cam.set_led(False, led_channel)
            time.sleep(dt)
            self._cam.set_led(True, led_channel)
            time.sleep(dt)
