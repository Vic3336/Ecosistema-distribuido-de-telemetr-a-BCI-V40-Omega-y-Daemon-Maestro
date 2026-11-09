#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
V40-OMEGA CORE - HIGH-DENSITY BCI MASTER ECOSYSTEM DAEMON (PRODUCTION REVISION)
==============================================================================
"""

import asyncio
import time
import orjson
import lz4.frame
import hmac
import hashlib
import numpy as np
import os
import signal
import ctypes
from collections import deque
from typing import Tuple, List, Optional

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    from scipy.signal import butter, lfilter, iirnotch
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

def lock_process_memory():
    MCL_CURRENT = 1
    MCL_FUTURE = 2
    try:
        libc = ctypes.CDLL(None)
        if libc.mlockall(MCL_CURRENT | MCL_FUTURE) != 0:
            raise RuntimeError()
        print("[SISTEMA] Memoria física bloqueada con éxito en RAM (mlockall).")
    except Exception:
        print("[SISTEMA ADVERTENCIA] No se pudo anclar la memoria. Verifique privilegios CAP_IPC_LOCK.")

class V40CircularStoreBuffer:
    def __init__(self, filepath: str = "v40_master_ring.bin"):
        self.filepath = filepath
        self.lock = asyncio.Lock()
        
    async def flush_packet_async(self, packet_bytes: bytes) -> None:
        if not packet_bytes:
            return
        async with self.lock:
            try:
                await asyncio.to_thread(self._append_to_disk, packet_bytes)
            except Exception as e:
                print(f"[ALMACÉN ERROR] Fallo en persistencia incremental: {e}")

    def _append_to_disk(self, block: bytes) -> None:
        with open(self.filepath, "ab") as f:
            f.write(len(block).to_bytes(4, 'big') + block)

class V40AdaptiveDSP:
    def __init__(self, num_channels: int = 32, window_size: int = 40, threshold: float = 3.0, fs: float = 250.0):
        self.num_channels = num_channels
        self.window_size = window_size
        self.threshold = threshold
        self.fs = fs
        self.history: deque = deque(maxlen=window_size)
        
        if SCIPY_AVAILABLE:
            nyq = 0.5 * fs
            low = 1.0 / nyq
            high = 45.0 / nyq
            self.b_bp, self.a_bp = butter(4, [low, high], btype='band')
            
            freq_notch = 60.0 / nyq
            quality_factor = 30.0
            self.b_notch, self.a_notch = iirnotch(freq_notch, quality_factor)
        else:
            print("[DSP ADVERTENCIA] SciPy no disponible. Filtros digitales desactivados.")

    def _apply_filters(self, data: np.ndarray) -> np.ndarray:
        if not SCIPY_AVAILABLE:
            return data
        filtered = lfilter(self.b_bp, self.a_bp, data, axis=0)
        filtered = lfilter(self.b_notch, self.a_notch, filtered, axis=0)
        return filtered

    def analyze(self, channels: List[float]) -> Tuple[bool, List[float]]:
        if not channels or len(channels) != self.num_channels:
            return False, [0.0] * self.num_channels
        
        raw_frame = np.array(channels, dtype=np.float32)
        self.history.append(raw_frame)
        
        if len(self.history) < 2:
            return False, [0.0] * self.num_channels

        matrix_history = np.array(self.history, dtype=np.float32)
        filtered_matrix = self._apply_filters(matrix_history)
        
        current_filtered_frame = filtered_matrix[-1]
        hist_mean = np.mean(filtered_matrix, axis=0)
        hist_std = np.std(filtered_matrix, axis=0)
        
        hist_std = np.where(hist_std == 0, 1e-6, hist_std)
        z_scores = np.abs(current_filtered_frame - hist_mean) / hist_std
        
        anomalies_per_channel = z_scores > self.threshold
        global_anomaly_detected = bool(np.any(anomalies_per_channel))
        
        return global_anomaly_detected, z_scores.tolist()

class V40ActuatorController:
    def __init__(self, port: str = "/dev/ttyACM0", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.connection: Optional[serial.Serial] = None
        
    def connect(self) -> None:
        if not SERIAL_AVAILABLE:
            print("[ACTUADOR] Módulo serial no disponible. Modo simulación activo.")
            return
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"[ACTUADOR] Enlace serial establecido en el puerto {self.port}")
        except Exception as e:
            print(f"[ACTUADOR ERROR] No se pudo abrir la interfaz serial: {e}. Modo seguro activo.")

    def transmit_command(self, payload: bytes) -> None:
        if self.connection and self.connection.is_open:
            try:
                self.connection.write(payload)
            except Exception as e:
                print(f"[ACTUADOR ERROR] Error de transmisión en bus físico: {e}")
                self.trigger_veto_protocol()

    def trigger_veto_protocol(self) -> None:
        print("[FAILSAFE ACTUADOR] ¡VETO ACTIVADO! Enviando señal de desconexión segura...")
        emergency_signal = b"\x00\x00\x00\x00\xFF"
        if self.connection and self.connection.is_open:
            try:
                self.connection.write(emergency_signal)
                self.connection.flush()
            except Exception:
                pass

    def close(self) -> None:
        self.trigger_veto_protocol()
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("[ACTUADOR] Interfaz física cerrada.")

class V40MasterDaemon:
    def __init__(self, host: str, port: int, secret_key: bytes):
        self.host = host
        self.port = port
        self.secret_key = secret_key
        self.buffer_store = V40CircularStoreBuffer()
        self.dsp = V40AdaptiveDSP(num_channels=32)
        self.actuator = V40ActuatorController()
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self.server: Optional[asyncio.Server] = None

    def verify_signature(self, compressed_payload: bytes, signature_hex: str) -> bool:
        expected = hmac.new(self.secret_key, compressed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_hex)

    async def handle_client_stream(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info('peername')
        print(f"[V40-CORE] Enlace de transmisión autorizado desde: {peer}")
        self.actuator.connect()
        
        try:
            while self.is_running:
                line = await reader.readline()
                if not line:
                    break
                
                packet = orjson.loads(line)
                sig = packet.get("sig")
                compressed_hex = packet.get("data")
                
                if not sig or not compressed_hex:
                    continue
                
                compressed_bytes = bytes.fromhex(compressed_hex)
                
                if not self.verify_signature(compressed_bytes, sig):
                    print(f"[ALERTA SEGURIDAD] Firma inválida desde {peer}. Invocando veto.")
                    self.actuator.trigger_veto_protocol()
                    break
                
                decompressed = lz4.frame.decompress(compressed_bytes)
                telemetry_data = orjson.loads(decompressed)
                
                channels = telemetry_data.get("channels", [])
                anomaly, z_scores = self.dsp.analyze(channels)
                
                if anomaly:
                    electrodes_afectados = [i for i, z in enumerate(z_scores) if z > self.dsp.threshold]
                    print(f"[DSP ALERTA MULTICANAL] Anomalía en canales {electrodes_afectados}.")
                    self.actuator.trigger_veto_protocol()
                else:
                    clean_command = b"\x01" + bytes([int(np.clip(np.mean(channels), 0, 255))]) + b"\x00\x02"
                    self.actuator.transmit_command(clean_command)
                
                await self.buffer_store.flush_packet_async(line)
                
        except Exception as e:
            print(f"[NODO ERROR] Excepción durante el procesamiento de stream: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.actuator.close()
            print(f"[-] Conexión cerrada con: {peer}")

    async def start(self) -> None:
        lock_process_memory()
        self.is_running = True
        self.server = await asyncio.start_server(self.handle_client_stream, self.host, self.port)
        print(f"[V40-CORE] Master Daemon desplegado en {self.host}:{self.port}")
        
        async with self.server:
            await self._shutdown_event.wait()
            
        print("[V40-CORE] Servidor TCP detenido de forma segura.")

    def shutdown(self) -> None:
        print("\n[V40-CORE] Recibida señal de interrupción. Apagado limpio...")
        self.is_running = False
        if self.server:
            self.server.close()
        self._shutdown_event.set()

def setup_signals(daemon: V40MasterDaemon) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, daemon.shutdown)
  
if __name__ == "__main__":
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 8888))
    SECRET_KEY = os.environ.get("MARLETTE_HMAC_SECRET", "V40_OMEGA_DEFAULT_SECURE_KEY_2027").encode()

    daemon = V40MasterDaemon(host=HOST, port=PORT, secret_key=SECRET_KEY)
    
    loop = asyncio.get_event_loop()
    try:
        setup_signals(daemon)
        loop.run_until_complete(daemon.start())
    except KeyboardInterrupt:
        daemon.shutdown()
    finally:
        loop.close()
        
