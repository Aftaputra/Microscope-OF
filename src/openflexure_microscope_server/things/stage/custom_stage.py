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
from ..serial_manager import serial_manager  # Import dari folder things

# ============================================================
# KONFIGURASI SERIAL — sesuaikan dengan port ESP
# ============================================================
SERIAL_PORT = "COM3"   # Windows: "COM3", "COM4", dll
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
        self._port = port or SERIAL_PORT
        self._hardware_position = {"x": 0, "y": 0, "z": 0}
        print(f"[Stage] __init__ called: simulate={simulate}, port={self._port}")
        super().__init__(thing_server_interface)

    def __enter__(self) -> Self:
        """Inisialisasi koneksi serial."""
        print(f"[Stage] __enter__ called: simulate={self._simulate}, port={self._port}")
        
        # Inisialisasi shared connection
        success = serial_manager.initialize(
            port=self._port,
            baud_rate=BAUD_RATE,
            simulate=self._simulate
        )
        
        # Update simulate status berdasarkan hasil inisialisasi
        self._simulate = serial_manager.is_simulate()
        print(f"[Stage] After initialization: simulate={self._simulate}")
        
        # Test koneksi
        if not self._simulate:
            try:
                response = self._send(b"p?\n")
                print(f"[Stage] ESP response: {response}")
            except Exception as e:
                print(f"[Stage] Failed to communicate with ESP: {e}")
                self._simulate = True
        
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Tutup koneksi - hanya ditutup sekali."""
        print("[Stage] __exit__ called")
        # Tidak menutup di sini, biarkan serial_manager yang handle

    def _send(self, command: bytes) -> str:
        """Kirim command ke ESP dan return response."""
        if self._simulate or serial_manager.is_simulate():
            print(f"[SIM] STAGE >> {command.decode().strip()}")
            if command.strip() == b"p?":
                pos = self._hardware_position
                return f"{pos['x']} {pos['y']} {pos['z']}"
            return "done."
        
        try:
            response = serial_manager.send_command(command)
            print(f"[Stage] Command: {command.decode().strip()} -> Response: {response}")
            return response
        except RuntimeError as e:
            print(f"[Stage] Serial error: {e}")
            self._simulate = True
            raise

    # ── Method wajib dari BaseStage ──────────────────────────

    def _hardware_update_position(self) -> None:
        """Baca posisi dari ESP."""
        try:
            response = self._send(b"p?\n")
            if response:
                x, y, z = [int(v) for v in response.split()]
                self._hardware_position = {"x": x, "y": y, "z": z}
                print(f"[Stage] Position updated: x={x}, y={y}, z={z}")
        except (ValueError, AttributeError) as e:
            print(f"[Stage] Failed to parse position: {e}")
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