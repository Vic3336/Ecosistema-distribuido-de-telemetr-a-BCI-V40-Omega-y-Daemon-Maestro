# ==========================================
# ETAPA 1: Constructor (Builder)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Instalar herramientas esenciales de compilación si tus paquetes requieren compilar código C
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de configuración del proyecto
COPY pyproject.toml .

# Actualizar pip, extraer dependencias de pyproject.toml y generar los archivos Wheel (.whl)
RUN pip install --no-cache-dir --upgrade pip && \
    python3 -c "import tomllib; f=open('pyproject.toml','rb'); d=tomllib.load(f); open('reqs.txt', 'w').write('\n'.join(d['project']['dependencies']))" && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r reqs.txt && \
    rm reqs.txt

# ==========================================
# ETAPA 2: Imagen Final (Runtime)
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Crear un usuario de sistema no raíz por seguridad e infraestructura limpia
RUN useradd -u 10001 -m appuser && \
    chown -R appuser:appuser /app

# Copiar únicamente los paquetes pre-compilados (Wheels) desde la etapa anterior
COPY --from=builder /build/wheels /app/wheels
COPY --from=builder /build/pyproject.toml /app/pyproject.toml

# Copiar el código fuente de tu aplicación (Orquestador y módulos secundarios)
COPY --chown=appuser:appuser . /app/

# Instalar las dependencias locales usando los Wheels sin descargar nada de internet
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links=/app/wheels /app/wheels/*.whl && \
    rm -rf /app/wheels

# Cambiar al usuario no raíz para la ejecución del contenedor
USER appuser

# Definir el comando por defecto para arrancar el orquestador unificado
ENTRYPOINT ["python", "gema_orquestador/main.py"]
