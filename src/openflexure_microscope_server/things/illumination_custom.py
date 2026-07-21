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
from .serial_manager import serial_manager

SERIAL_PORT = "COM3"
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
        self._port = port or SERIAL_PORT
        self._brightness_cool = 0.0
        self._brightness_warm = 0.0
        print(f"[Illumination] __init__ called: simulate={simulate}, port={self._port}")
        super().__init__(thing_server_interface)

    def __enter__(self) -> Self:
        """Inisialisasi - gunakan shared connection."""
        print(f"[Illumination] __enter__ called: simulate={self._simulate}, port={self._port}")
        
        # Inisialisasi serial manager
        serial_manager.initialize(
            port=self._port,
            baud_rate=BAUD_RATE,
            simulate=self._simulate
        )
        self._simulate = serial_manager.is_simulate()
        print(f"[Illumination] After initialization: simulate={self._simulate}")
        
        return self

    def __exit__(self, *args) -> None:
        """Tidak menutup koneksi - biarkan serial_manager yang handle."""
        print("[Illumination] __exit__ called")
        pass

    def _send(self, command: bytes) -> str:
        """Kirim command ke ESP menggunakan shared connection."""
        print(f"[Illumination] _send called: {command.decode().strip()}, simulate={self._simulate}")
        
        # Auto-initialize jika belum
        if not serial_manager._is_initialized:
            print("[Illumination] Serial manager not initialized, initializing...")
            serial_manager.initialize(
                port=self._port,
                baud_rate=BAUD_RATE,
                simulate=self._simulate
            )
            self._simulate = serial_manager.is_simulate()
        
        if self._simulate or serial_manager.is_simulate():
            print(f"[SIM] ILLUMINATION >> {command.decode().strip()}")
            return "done."
        
        try:
            response = serial_manager.send_command(command)
            print(f"[Illumination] Command: {command.decode().strip()} -> Response: {response}")
            return response
        except RuntimeError as e:
            print(f"[Illumination] Serial error: {e}")
            self._simulate = True
            raise

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
        print(f"[Illumination] Setting brightness_cool: {value}")
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
        print(f"[Illumination] Setting brightness_warm: {value}")
        value = max(0.0, min(1.0, value))
        self._brightness_warm = value
        cw = int(self._brightness_cool * 255)
        ww = int(value * 255)
        self._send_led(cw, ww)

    @lt.action
    def set_led(self, led_on: bool = True) -> None:
        """Nyalain semua LED atau matiin semua."""
        print(f"[Illumination] set_led called: {led_on}")
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