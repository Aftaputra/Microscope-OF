"""Manajer koneksi serial bersama untuk stage dan illumination."""

import serial
from typing import Optional
import time


class SerialManager:
    """Singleton manager untuk koneksi serial bersama."""

    _instance = None
    _serial: Optional[serial.Serial] = None
    _port: Optional[str] = None
    _baud_rate: int = 115200
    _is_simulate: bool = False
    _is_initialized: bool = False
    _default_port: str = "COM3"
    _default_baud: int = 115200

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, port: str = None, baud_rate: int = 115200, simulate: bool = False):
        """Inisialisasi koneksi serial."""
        if port is None:
            port = cls._default_port

        print(f"[SerialManager] initialize called with port={port}, simulate={simulate}")

        if cls._is_initialized:
            print(f"[SerialManager] Already initialized with port {cls._port}")
            return True

        cls._port = port
        cls._baud_rate = baud_rate
        cls._is_simulate = simulate

        if not simulate:
            try:
                print(f"[SerialManager] Opening port {port} at {baud_rate} baud...")
                cls._serial = serial.Serial(
                    port=port,
                    baudrate=baud_rate,
                    timeout=3,
                    write_timeout=2,
                    dsrdtr=False,   # cegah Arduino auto-reset via DTR
                    rtscts=False,   # cegah Arduino auto-reset via RTS
                )
                print(f"[SerialManager] Waiting for Arduino to boot...")
                time.sleep(3)  # tunggu Arduino selesai boot

                # Flush buffer yang mungkin berisi garbage dari boot
                cls._serial.reset_input_buffer()

                # Test koneksi
                cls._serial.write(b"p?\n")
                response = cls._serial.readline()

                if response:
                    print(f"[SerialManager] Port {port} opened successfully")
                    print(f"[SerialManager] Arduino response: {response.decode().strip()}")
                    cls._is_initialized = True
                    return True
                else:
                    print(f"[SerialManager] No response from Arduino on {port}")
                    cls._serial.close()
                    cls._serial = None
                    cls._is_simulate = True
                    cls._is_initialized = True
                    return False

            except Exception as e:
                print(f"[SerialManager] Failed to open port {port}: {e}")
                cls._serial = None
                cls._is_simulate = True
                cls._is_initialized = True
                return False
        else:
            print(f"[SerialManager] Running in simulation mode")
            cls._is_initialized = True
            return True

    @classmethod
    def ensure_initialized(cls, port: str = None, simulate: bool = False):
        """Pastikan serial manager sudah diinisialisasi."""
        if not cls._is_initialized:
            print("[SerialManager] Not initialized, initializing now...")
            cls.initialize(port=port or cls._default_port, simulate=simulate)
        return cls._is_initialized

    @classmethod
    def get_serial(cls) -> Optional[serial.Serial]:
        """Dapatkan koneksi serial."""
        if cls._is_simulate:
            return None
        return cls._serial

    @classmethod
    def is_simulate(cls) -> bool:
        """Cek apakah dalam mode simulasi."""
        return cls._is_simulate

    @classmethod
    def is_connected(cls) -> bool:
        """Cek apakah koneksi serial terbuka."""
        return cls._serial is not None and cls._serial.is_open

    @classmethod
    def send_command(cls, command: bytes, port: str = None, simulate: bool = False) -> str:
        """Kirim command dan terima response."""
        # Auto-initialize jika belum siap
        if not cls._is_initialized:
            print("[SerialManager] Auto-initializing...")
            cls.initialize(port=port or cls._default_port, simulate=simulate)

        if cls._is_simulate:
            print(f"[SIM] >> {command.decode().strip()}")
            return "done."

        if cls._serial is None or not cls._serial.is_open:
            print(f"[SerialManager] Port tidak terbuka, coba reconnect...")
            cls._is_initialized = False
            cls.initialize(port=cls._port, baud_rate=cls._baud_rate, simulate=False)
            if cls._is_simulate:
                print("[SerialManager] Reconnect gagal, fallback ke simulate")
                return "done."

        try:
            # Flush buffer sebelum kirim
            cls._serial.reset_input_buffer()

            # Kirim command
            cls._serial.write(command)
            cls._serial.flush()

            # Baca response
            response = cls._serial.readline().decode().strip()

            if not response:
                print("[SerialManager] Timeout — no response from Arduino")
                raise RuntimeError("No response from Arduino (timeout)")

            print(f"[Arduino] >> {command.decode().strip()} → {response}")
            return response

        except serial.SerialException as e:
            print(f"[SerialManager] Serial error: {e}")
            cls._serial = None
            raise RuntimeError(f"Serial communication error: {e}")

        except RuntimeError:
            raise

        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")

    @classmethod
    def close(cls):
        """Tutup koneksi serial."""
        if cls._serial and cls._serial.is_open:
            cls._serial.close()
            print(f"[SerialManager] Port {cls._port} closed")
        cls._serial = None
        cls._is_initialized = False


# Instance global
serial_manager = SerialManager()