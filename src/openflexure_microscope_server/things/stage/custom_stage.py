"""Custom stage Thing untuk board ESP tim hardware.
Engineer: isi bagian SERIAL COMMAND TEMPLATE di bawah sesuai firmware kalian.
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
# SERIAL COMMAND TEMPLATE — ENGINEER ISI BAGIAN INI
# ============================================================
SERIAL_PORT = "/dev/ttyUSB0"   # di Windows: "COM3", "COM4", dll
BAUD_RATE = 115200

def cmd_move_z(steps: int) -> bytes:
    """Command buat gerak motor fokus (Z) sejumlah steps."""
    return f"MOVE Z {steps}\n".encode()  # ← sesuaikan format

def cmd_stop() -> bytes:
    """Command buat stop motor."""
    return b"STOP\n"  # ← sesuaikan format

def cmd_is_moving() -> bytes:
    """Command buat cek apakah motor masih bergerak."""
    return b"MOVING?\n"  # ← sesuaikan format

def parse_is_moving(response: str) -> bool:
    """Parse response dari cmd_is_moving. Return True kalau masih bergerak."""
    return response.strip().lower() == "true"  # ← sesuaikan format response

def cmd_zero_position() -> bytes:
    """Command buat reset posisi ke nol."""
    return b"ZERO\n"  # ← sesuaikan format

STEPS_PER_MOVE = 100   # estimasi steps per gerakan, buat estimasi durasi
STEP_TIME = 0.001      # estimasi waktu per step (detik)
# ============================================================

class CustomStage(BaseStage):
    """Stage Thing untuk board custom ESP tim hardware.
    
    Hanya punya axis Z (fokus). Axis X dan Y tidak ada motor fisik,
    tapi tetap didefinisikan karena BaseStage dan camera_stage_mapping
    butuh X/Y/Z.
    """

    _axis_names = ("x", "y", "z")

    def __init__(self, thing_server_interface: lt.ThingServerInterface, simulate: bool = False) -> None:
        self._simulate = simulate
        self._serial = None
        self._hardware_position = {"x": 0, "y": 0, "z": 0}
        super().__init__(thing_server_interface)

    def __enter__(self) -> Self:
        if not self._simulate:
            self._serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Tutup koneksi serial saat server stop."""
        if self._serial and self._serial.is_open:
            self._serial.close()

    def _send(self, command: bytes) -> str:
        if self._simulate:
            print(f"[SIM] STAGE >> {command.decode().strip()}")
            return "ok"
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Serial port tidak terbuka.")
        self._serial.write(command)
        return self._serial.readline().decode().strip()

    # ── Method wajib dari BaseStage ──────────────────────────

    def _hardware_update_position(self) -> None:
        """Baca posisi dari hardware. 
        ESP kita belum expose query posisi, jadi track internal aja dulu.
        """
        pass  # _hardware_position sudah diupdate di move functions

    def _hardware_move_relative(
        self, block_cancellation: bool = False, **kwargs: int
    ) -> None:
        z_steps = kwargs.get("z", 0)
        if z_steps != 0:
            self._send(cmd_move_z(z_steps))
            if not self._simulate:  # skip sleep di simulation mode
                duration = self._estimate_move_duration([z_steps])
                time.sleep(duration)
        for axis, steps in kwargs.items():
            if axis in self._hardware_position:
                self._hardware_position[axis] += steps

    def _hardware_move_absolute(
        self, block_cancellation: bool = False, **kwargs: int
    ) -> None:
        """Gerak absolut — hitung displacement dari posisi sekarang."""
        displacement = {
            axis: int(target) - self._hardware_position.get(axis, 0)
            for axis, target in kwargs.items()
        }
        self._hardware_move_relative(
            block_cancellation=block_cancellation, **displacement
        )

    def _hardware_start_move_relative(self, displacement: Sequence[int]) -> None:
        """Mulai gerak tanpa blocking (buat jog)."""
        z_index = list(self._axis_names).index("z")
        z_steps = displacement[z_index] if z_index < len(displacement) else 0
        if z_steps != 0:
            self._send(cmd_move_z(z_steps))

    def _hardware_stop(self) -> None:
        """Stop motor."""
        self._send(cmd_stop())

    def _poll_moving(self) -> bool:
        """Cek apakah motor masih bergerak."""
        response = self._send(cmd_is_moving())
        return parse_is_moving(response)

    def _estimate_move_duration(self, displacement: Sequence[int]) -> float:
        """Estimasi durasi gerak dalam detik."""
        max_disp = max(abs(d) for d in displacement) if displacement else 0
        return max_disp * STEP_TIME

    @lt.action
    def set_zero_position(self) -> None:
        """Reset posisi ke nol."""
        self._send(cmd_zero_position())
        self._hardware_position = dict.fromkeys(self._axis_names, 0)