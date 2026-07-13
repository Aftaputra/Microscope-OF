"""Custom stage Thing untuk board ESP tim hardware.
Protokol serial sesuai List_Sangaboard dari engineer.
"""

from __future__ import annotations
import time
import threading
from collections.abc import Sequence
from typing import Optional, Self
from types import TracebackType
import serial
import labthings_fastapi as lt
from . import BaseStage

# ============================================================
# KONFIGURASI SERIAL — sesuaikan dengan port ESP
# ============================================================
SERIAL_PORT = "/dev/ttyUSB0"   # Windows: "COM3", "COM4", dll
BAUD_RATE = 115200
STEP_TIME = 0.001  # estimasi waktu per step (detik)
# ============================================================


class CustomStage(BaseStage):
    """Stage Thing untuk board custom ESP dengan motor X, Y, Z."""

    _axis_names = ("x", "y", "z")

    def __init__(
        self,
        thing_server_interface: lt.ThingServerInterface,
        simulate: bool = False,
        port: Optional[str] = None,
    ) -> None:
        self._simulate = simulate
        self._serial: Optional[serial.Serial] = None
        self._port = port or SERIAL_PORT
        self._hardware_position = {"x": 0, "y": 0, "z": 0}
        super().__init__(thing_server_interface)

    def __enter__(self) -> Self:
        if not self._simulate:
            self._serial = serial.Serial(self._port, BAUD_RATE, timeout=2)
            time.sleep(2)  # tunggu ESP reset
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if self._serial and self._serial.is_open:
            self._send(b"release\n")
            self._serial.close()

    def _send(self, command: bytes) -> str:
        """Kirim command ke ESP dan return response."""
        if self._simulate:
            print(f"[SIM] STAGE >> {command.decode().strip()}")
            # Simulasi response p? dengan posisi saat ini
            if command.strip() == b"p?":
                pos = self._hardware_position
                return f"{pos['x']} {pos['y']} {pos['z']}"
            return "done."
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Serial port tidak terbuka.")
        self._serial.write(command)
        return self._serial.readline().decode().strip()

    # ── Method wajib dari BaseStage ──────────────────────────

    def _hardware_update_position(self) -> None:
        """Baca posisi dari ESP."""
        response = self._send(b"p?\n")
        try:
            x, y, z = [int(v) for v in response.split()]
            self._hardware_position = {"x": x, "y": y, "z": z}
        except (ValueError, AttributeError):
            pass  # keep last known position if parse fails

    def _hardware_move_relative(
        self, block_cancellation: bool = False, **kwargs: int
    ) -> None:
        """Gerak relatif — kirim command mr x y z ke ESP."""
        x = kwargs.get("x", 0)
        y = kwargs.get("y", 0)
        z = kwargs.get("z", 0)

        if x != 0 or y != 0 or z != 0:
            cmd = f"mr {x} {y} {z}\n".encode()
            self._send(cmd)
            if not self._simulate:
                # tunggu response "done."
                duration = self._estimate_move_duration([x, y, z])
                time.sleep(duration)

        # update posisi internal
        for axis, steps in {"x": x, "y": y, "z": z}.items():
            self._hardware_position[axis] = self._hardware_position.get(axis, 0) + steps

    def _hardware_move_absolute(
        self, block_cancellation: bool = False, **kwargs: int
    ) -> None:
        """Gerak absolut — hitung displacement dari posisi sekarang."""
        self._hardware_update_position()
        displacement = {
            axis: int(target) - self._hardware_position.get(axis, 0)
            for axis, target in kwargs.items()
        }
        self._hardware_move_relative(
            block_cancellation=block_cancellation, **displacement
        )

    def _hardware_start_move_relative(self, displacement: Sequence[int]) -> None:
        """Mulai gerak tanpa blocking (buat jog)."""
        axes = self._axis_names
        x = displacement[0] if len(displacement) > 0 else 0
        y = displacement[1] if len(displacement) > 1 else 0
        z = displacement[2] if len(displacement) > 2 else 0
        if x != 0 or y != 0 or z != 0:
            cmd = f"mr {x} {y} {z}\n".encode()
            self._send(cmd)

    def _hardware_stop(self) -> None:
        """Release motor (stop)."""
        self._send(b"release\n")

    def _poll_moving(self) -> bool:
        """ESP kita blocking — kalau response sudah 'done.' berarti berhenti."""
        return False  # always done after send

    def _estimate_move_duration(self, displacement: Sequence[int]) -> float:
        """Estimasi durasi gerak dalam detik."""
        max_disp = max(abs(d) for d in displacement) if displacement else 0
        return max_disp * STEP_TIME

    @lt.action
    def set_zero_position(self) -> None:
        """Reset posisi ke nol."""
        self._send(b"zero\n")
        self._hardware_position = dict.fromkeys(self._axis_names, 0)

    @lt.action
    def release_motors(self) -> None:
        """Release semua motor (matikan coil)."""
        self._send(b"release\n")