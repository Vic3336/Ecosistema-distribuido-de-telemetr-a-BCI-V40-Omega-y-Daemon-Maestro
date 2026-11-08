#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
GEMA ORQUESTADOR - UNIFIED CLI MANAGEMENT ENTRYPOINT
==============================================================================
Punto de entrada unificado para el ecosistema distribuido V40-Omega BCI.
"""

import sys
import argparse
import os

def launch_master_daemon(args):
    print("[GEMA INFO] Inicializando el subsistema V40 Master Ecosystem Daemon...")
    try:
        import asyncio
        from gema_orquestador.daemon import V40MasterDaemon, setup_signals
        
        secret = os.environ.get("MARLETTE_HMAC_SECRET", args.secret).encode()
        if len(secret) < 32:
            print("[GEMA ADVERTENCIA] La firma HMAC utiliza una clave débil o por defecto.")

        daemon = V40MasterDaemon(host=args.host, port=args.port, secret_key=secret)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(asyncio.sleep(0))
        setup_signals(daemon)
        
        loop.run_until_complete(daemon.start())
    except ImportError as e:
        print(f"[GEMA CRÍTICO] Error de dependencias al cargar el Daemon: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[GEMA CRÍTICO] Falla catastrófica en el entorno de ejecución del Daemon: {e}")
        sys.exit(1)

def launch_relay_client(args):
    print(f"[GEMA INFO] Conectando V40 Relay Client hacia el nodo central [{args.target_host}:{args.target_port}]...")
    try:
        import asyncio
        from gema_orquestador.network.client import start_relay_node
        
        asyncio.run(start_relay_node(host=args.target_host, port=args.target_port))
    except KeyboardInterrupt:
        print("\n[GEMA INFO] Transmisión del Relay Client finalizada por el usuario.")
    except Exception as e:
        print(f"[GEMA CRÍTICO] Falla en la ejecución del Relay Client: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Gema Orquestador v40-Omega BCI Core Command Line Interface",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcomandos operativos disponibles")

    master_parser = subparsers.add_parser("server", help="Desplegar el V40 Master Ecosystem Daemon")
    master_parser.add_argument("--host", type=str, default="0.0.0.0", help="Dirección IP de escucha del servidor")
    master_parser.add_argument("--port", type=int, default=8888, help="Puerto de red TCP asignado")
    master_parser.add_argument("--secret", type=str, default="V40_OMEGA_DEFAULT_SECURE_KEY_2027", 
                               help="Clave secreta alternativa de verificación hmac")

    client_parser = subparsers.add_parser("client", help="Desplegar el V40 Relay Client")
    client_parser.add_argument("--target-host", type=str, default="127.0.0.1", help="Dirección IP del Daemon central")
    client_parser.add_argument("--target-port", type=int, default=8888, help="Puerto TCP destino del Daemon")

    args = parser.parse_args()

    if args.command == "server":
        launch_master_daemon(args)
    elif args.command == "client":
        launch_relay_client(args)

if __name__ == "__main__":
    main()
