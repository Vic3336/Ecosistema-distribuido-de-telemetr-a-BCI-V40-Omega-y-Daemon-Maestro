# V40-Omega BCI Core Ecosistema Distribuido

Ecosistema distribuido de telemetría BCI de alta densidad (32 canales). Diseñado para la adquisición, procesamiento en tiempo real, compresión y transmisión ultra-segunda de señales cerebrales.

## 🚀 Arquitectura del Sistema

* **Daemon Maestro (`daemon.py`)**: Servicio central con anclaje de memoria física (`mlockall`), filtrado digital adaptativo mediante SciPy (pasa-banda y notch), y análisis de anomalías multicanal basado en puntajes Z.
* **Cliente Periférico (`client.py`)**: Nodo de retransmisión optimizado para muestreo estable a 250 Hz con compensación de Jitter, compresión instantánea en formato LZ4 y autenticación criptográfica HMAC-SHA256.
* **Interfaz CLI (`cli.py`)**: Orquestador unificado de comandos para el despliegue rápido de servidores y clientes.
* **Contenerización y Empaquetado**: Manifiesto PEP 517/621 (`pyproject.toml`) y `Dockerfile` multi-etapa con lectura de dependencias mediante `tomllib`.

## 📦 Instalación y Uso

Instalación local en modo editable:
```bash
pip install -e .
