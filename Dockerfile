# ==============================================================================
# ETAPA 1: Compilación de Dependencias Binarias y Ruedas (Wheels)
# ==============================================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r <(python3 -c "import tomllib; f=open('pyproject.toml','rb'); d=tomllib.load(f); print('\n'.join(d['project']['dependencies']))")

# ==============================================================================
# ETAPA 2: Entorno de Ejecución en Producción (Runtime Ultra-Liviano)
# ==============================================================================
FROM python:3.11-slim-bookworm

WORKDIR /app

COPY --from=builder /build/wheels /wheels

RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

COPY gema_orquestador/ /app/gema_orquestador/
COPY pyproject.toml /app/

RUN pip install --no-cache-dir -e .

EXPOSE 8888

ENV MARLETTE_HMAC_SECRET="V40_OMEGA_DEFAULT_SECURE_KEY_2027"
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["gema"]
CMD ["server", "--host", "0.0.0.0", "--port", "8888"]
