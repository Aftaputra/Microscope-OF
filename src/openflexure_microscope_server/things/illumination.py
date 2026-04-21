"""A module to handle the illumination in LabThings."""

import time
from typing import Literal

import labthings_fastapi as lt

from .camera.simulation import SimulatedCamera
from .stage.sangaboard import SangaboardThing


class Illumination(lt.Thing):
    """Base class for an illumination controller."""

    _class_settings = {"validate_properties_on_set": True}

    @lt.action
    def set_led(self, led_on: bool = True) -> None:
        """Set the LED to on or off."""
        raise NotImplementedError(
            "Turning the LED on and off should be implemented by child classes."
        )

    @lt.action
    def flash(self, number_of_flashes: int = 10, dt: float = 0.5) -> None:
        """Flash the illumination source.

        :param number_of_flashes: Number of times to flash the LED.
        :param dt: Flash duration in seconds.
        """
        for _ in range(number_of_flashes):
            self.set_led(False)
            time.sleep(dt)
            self.set_led(True)
            time.sleep(dt)


class SangaIllumination(Illumination):
    """Illumination driven by a Sangaboard."""

    _stage: SangaboardThing = lt.thing_slot()

    @lt.action
    def set_led(
        self,
        led_on: bool = True,
        led_channel: Literal["cc"] = "cc",
    ) -> None:
        """Set the LED to on or off."""
        self._stage.set_led(led_on, led_channel)


class SimulatorIllumination(Illumination):
    """Illumination control in the simulator."""

    _cam: SimulatedCamera = lt.thing_slot()

    @lt.action
    def set_led(self, led_on: bool = True) -> None:
        """Set the LED to on or off."""
        self._cam.set_led(led_on)
