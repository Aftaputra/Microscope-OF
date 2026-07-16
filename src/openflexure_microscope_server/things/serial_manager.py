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
    _default_port: str = "COM4"
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
            return cls._is_simulate == simulate and cls._port == port
        
        cls._port = port
        cls._baud_rate = baud_rate
        cls._is_simulate = simulate
        
        if not simulate:
            try:
                print(f"[SerialManager] Opening port {port} at {baud_rate} baud...")
                cls._serial = serial.Serial(
                    port=port,
                    baudrate=baud_rate,
                    timeout=2,
                    write_timeout=2
                )
                time.sleep(2)  # Tunggu ESP reset
                
                # Test koneksi
                cls._serial.write(b"p?\n")
                response = cls._serial.readline()
                if response:
                    print(f"[SerialManager] Port {port} opened successfully")
                    print(f"[SerialManager] ESP response: {response.decode().strip()}")
                    cls._is_initialized = True
                    return True
                else:
                    print(f"[SerialManager] No response from ESP on {port}")
                    cls._is_simulate = True
                    cls._serial = None
                    cls._is_initialized = True
                    return False
                    
            except Exception as e:
                print(f"[SerialManager] Failed to open port {port}: {e}")
                cls._is_simulate = True
                cls._serial = None
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
        
        print(f"[SerialManager] send_command called: {command.decode().strip()}")
        print(f"[SerialManager] State: simulate={cls._is_simulate}, port={cls._port}, initialized={cls._is_initialized}")
        
        if cls._is_simulate:
            print(f"[SIM] Sending command: {command.decode().strip()}")
            return "done."
        
        if cls._serial is None or not cls._serial.is_open:
            # Coba reconnect
            print(f"[SerialManager] Serial port not open, trying to reconnect...")
            cls.initialize(port=cls._port, simulate=False)
            if cls._serial is None or not cls._serial.is_open:
                raise RuntimeError(f"Serial port {cls._port} tidak terbuka.")
        
        try:
            # Bersihkan buffer
            cls._serial.reset_input_buffer()
            
            # Kirim command
            cls._serial.write(command)
            cls._serial.flush()
            
            # Baca response
            response = cls._serial.readline().decode().strip()
            
            if not response:
                raise RuntimeError("No response from ESP (timeout)")
                
            return response
            
        except Exception as e:
            raise RuntimeError(f"Serial communication error: {e}")
    
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