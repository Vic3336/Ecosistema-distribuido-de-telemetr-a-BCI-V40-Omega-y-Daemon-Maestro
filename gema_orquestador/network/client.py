#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
V40-OMEGA RELAY CLIENT - PERIPHERAL TELEMETRY NODE (PRODUCTION REVISION)
==============================================================================
"""

import asyncio
import time
import orjson
import lz4.frame
import hmac
import hashlib
import os
import numpy as np

async def start_relay_node(host: str = "127.0.0.1", port: int = 8888, secret_key: bytes = None):
    if secret_key is None:
        secret_key = os.environ.get("MARLETTE_HMAC_SECRET", "V40_OMEGA_DEFAULT_SECURE_KEY_2027").encode()

    print(f"[RELAY CLIENT] Inicializando nodo periférico V40-Omega...")
    print(f"  -> Destino Maestro : {host}:{port}")

    sampling_rate = 250.0
    nominal_interval = 1.0 / sampling_rate
    seq = 0

    while True:
        try:
            print(f"[RELAY CLIENT] Estableciendo enlace TCP con el Daemon central en {host}:{port}...")
            reader, writer = await asyncio.open_connection(host, port)
            print(f"[RELAY CLIENT] Enlace activo. Transmitiendo telemetría a {sampling_rate} Hz...")

            while True:
                loop_start = asyncio.get_running_loop().time()

                channels = list(np.random.normal(0, 1.5, 32).astype(np.float32))
                
                payload_dict = {
                    "seq": seq,
                    "ts": time.time(),
                    "channels": channels
                }

                raw_json = orjson.dumps(payload_dict)
                compressed_bytes = lz4.frame.compress(raw_json, compression_level=0)
                sig = hmac.new(secret_key, compressed_bytes, hashlib.sha256).hexdigest()

                packet_dict = {
                    "sig": sig,
                    "data": compressed_bytes.hex()
                }
                
                packet_line = orjson.dumps(packet_dict) + b"\n"

                writer.write(packet_line)
                await writer.drain()

                seq += 1
                
                elapsed = asyncio.get_running_loop().time() - loop_start
                sleep_time = max(0.0, nominal_interval - elapsed)
                await asyncio.sleep(sleep_time)

        except (ConnectionRefusedError, asyncio.IncompleteReadError, OSError) as e:
            print(f"[RELAY ADVERTENCIA] Conexión interrumpida ({e}). Reintentando en 3 segundos...")
            await asyncio.sleep(3.0)
        except Exception as e:
            print(f"[RELAY ERROR] Excepción crítica en el nodo periférico: {e}")
            await asyncio.sleep(3.0)
          
