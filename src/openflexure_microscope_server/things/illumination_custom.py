"""Custom illumination Thing untuk LED PWM dual channel (cool + warm white).
Protokol: led <cw> <ww> — nilai 0-255
"""

from __future__ import annotations
from typing import Optional, Self
from types import TracebackType
import serial
import labthings_fastapi as lt
from .illumination import Illumination
from openflexure_microscope_server.ui import PropertyControl, property_control_for

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200


class CustomIllumination(Illumination):
    """Illumination Thing untuk LED PWM dual channel (cool white + warm white)."""

    def __init__(
        self,
        thing_server_interface: lt.ThingServerInterface,
        simulate: bool = False,
        port: Optional[str] = None,
    ) -> None:
        self._simulate = simulate
        self._serial: Optional[serial.Serial] = None
        self._port = port or SERIAL_PORT
        self._brightness_cool = 0.0
        self._brightness_warm = 0.0
        super().__init__(thing_server_interface)

    def __enter__(self) -> Self:
        if not self._simulate:
            self._serial = serial.Serial(self._port, BAUD_RATE, timeout=2)
        return self

    def __exit__(self, *args) -> None:
        if self._serial and self._serial.is_open:
            self._send_led(0, 0)
            self._serial.close()

    def _send(self, command: bytes) -> str:
        if self._simulate:
            print(f"[SIM] ILLUMINATION >> {command.decode().strip()}")
            return "done."
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Serial port tidak terbuka.")
        self._serial.write(command)
        return self._serial.readline().decode().strip()

    def _send_led(self, cw: int, ww: int) -> None:
        """Kirim command led ke ESP. cw dan ww adalah nilai 0-255."""
        self._send(f"led {cw} {ww}\n".encode())

    # ── Properties untuk UI ──────────────────────────────────

    @lt.setting
    def brightness_cool(self) -> float:
        """Brightness cool white LED (0.0 - 1.0)."""
        return self._brightness_cool

    @brightness_cool.setter
    def _set_brightness_cool(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._brightness_cool = value
        cw = int(value * 255)
        ww = int(self._brightness_warm * 255)
        self._send_led(cw, ww)

    @lt.setting
    def brightness_warm(self) -> float:
        """Brightness warm white LED (0.0 - 1.0)."""
        return self._brightness_warm

    @brightness_warm.setter
    def _set_brightness_warm(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._brightness_warm = value
        cw = int(self._brightness_cool * 255)
        ww = int(value * 255)
        self._send_led(cw, ww)

    @lt.action
    def set_led(self, led_on: bool = True) -> None:
        """Nyalain semua LED atau matiin semua."""
        if led_on:
            cw = int(self._brightness_cool * 255)
            ww = int(self._brightness_warm * 255)
        else:
            cw, ww = 0, 0
        self._send_led(cw, ww)

    @lt.property
    def manual_illumination_settings(self) -> list[PropertyControl]:
        """Expose brightness sliders ke UI."""
        return [
            property_control_for(self, "brightness_cool", label="Cool White"),
            property_control_for(self, "brightness_warm", label="Warm White"),
        ]