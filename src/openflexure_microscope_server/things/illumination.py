import time
from typing import Literal

import labthings_fastapi as lt


class Illumination(lt.Thing):
    """Abstract illumination controller."""

    brightness: float = lt.property(
        default=0.0,
        description="Illumination brightness (0-1)",
    )

    @lt.action
    def set_brightness(self, brightness: float) -> None:
        self.brightness = brightness

    @lt.action
    def flash(
        self,
        number_of_flashes: int = 10,
        dt: float = 0.5,
    ) -> None:
        """Flash the illumination source."""
        for _ in range(number_of_flashes):
            self.set_brightness(1.0)
            time.sleep(dt)
            self.set_brightness(0.0)
            time.sleep(dt)


class SangaIllumination(Illumination):
    """Illumination driven by a Sangaboard."""

    sangaboard = lt.thing_slot(description="Sangaboard providing LED control")

    @lt.action
    def set_brightness(self, brightness: float) -> None:
        self.sangaboard.set_led_brightness(brightness)
        self.brightness = brightness

    @lt.action
    def flash(
        self,
        number_of_flashes: int = 10,
        dt: float = 0.5,
        led_channel: Literal["cc"] = "cc",
    ) -> None:
        for _ in range(number_of_flashes):
            self.sangaboard.set_led(True, led_channel)
            time.sleep(dt)
            self.sangaboard.set_led(False, led_channel)
            time.sleep(dt)
