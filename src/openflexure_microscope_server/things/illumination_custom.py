"""Custom illumination Thing untuk LED PWM dual channel (cool + warm white).
Engineer: isi bagian SERIAL COMMAND TEMPLATE di bawah sesuai firmware kalian.
"""

import serial
import labthings_fastapi as lt
from .illumination import Illumination
from openflexure_microscope_server.ui import PropertyControl, property_control_for

# ============================================================
# SERIAL COMMAND TEMPLATE — ENGINEER ISI BAGIAN INI
# ============================================================
SERIAL_PORT = "/dev/ttyUSB0"   # sama dengan CustomStage kalau satu board
BAUD_RATE = 115200

def cmd_set_cool(brightness: float) -> bytes:
    """Set brightness cool white LED. brightness: 0.0 - 1.0"""
    pwm = int(brightness * 255)
    return f"LED COOL {pwm}\n".encode()  # ← sesuaikan format

def cmd_set_warm(brightness: float) -> bytes:
    """Set brightness warm white LED. brightness: 0.0 - 1.0"""
    pwm = int(brightness * 255)
    return f"LED WARM {pwm}\n".encode()  # ← sesuaikan format
# ============================================================

class CustomIllumination(Illumination):
    """Illumination Thing untuk LED PWM dual channel."""

    def __init__(self, thing_server_interface: lt.ThingServerInterface, simulate: bool = False) -> None:
        self._simulate = simulate
        self._serial = None
        self._brightness_cool = 0.0
        self._brightness_warm = 0.0
        super().__init__(thing_server_interface)

    def __enter__(self):
        if not self._simulate:
            self._serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        return self

    @lt.property
    def manual_illumination_settings(self) -> list[PropertyControl]:
        """Expose brightness sliders ke UI."""
        return [
            property_control_for(self, "brightness_cool", label="Cool White (0-1)"),
            property_control_for(self, "brightness_warm", label="Warm White (0-1)"),
        ]
    
    def __exit__(self, *args):
        if self._serial and self._serial.is_open:
            self.set_led(False)
            self._serial.close()

    def _send(self, command: bytes) -> str:
        if self._simulate:
            print(f"[SIM] ILLUMINATION >> {command.decode().strip()}")
            return "ok"
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Serial port tidak terbuka.")
        self._serial.write(command)
        return self._serial.readline().decode().strip()

    @lt.setting
    def brightness_cool(self) -> float:
        """Brightness cool white LED (0.0 - 1.0)."""
        return self._brightness_cool

    @brightness_cool.setter
    def _set_brightness_cool(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._brightness_cool = value
        self._send(cmd_set_cool(value))

    @lt.setting
    def brightness_warm(self) -> float:
        """Brightness warm white LED (0.0 - 1.0)."""
        return self._brightness_warm

    @brightness_warm.setter
    def _set_brightness_warm(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        self._brightness_warm = value
        self._send(cmd_set_warm(value))

    @lt.action
    def set_led(self, led_on: bool = True) -> None:
        """Nyalain semua LED (ke brightness sebelumnya) atau matiin semua."""
        if led_on:
            self._send(cmd_set_cool(self._brightness_cool))
            self._send(cmd_set_warm(self._brightness_warm))
        else:
            self._send(cmd_set_cool(0))
            self._send(cmd_set_warm(0))