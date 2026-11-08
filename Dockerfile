# ==========================================
# ETAPA 1: Constructor (Builder)
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN pip install --no-cache-dir --upgrade pip && \
    python3 -c "import tomllib; f=open('pyproject.toml','rb'); d=tomllib.load(f); open('reqs.txt', 'w').write('\n'.join(d['project']['dependencies']))" && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r reqs.txt && \
    rm reqs.txt

# ==========================================
# ETAPA 2: Imagen Final (Runtime)
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

RUN useradd -u 10001 -m appuser && \
    chown -R appuser:appuser /app

COPY --from=builder /build/wheels /app/wheels
COPY --from=builder /build/pyproject.toml /app/pyproject.toml

COPY --chown=appuser:appuser . /app/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --no-index --find-links=/app/wheels /app/wheels/*.whl && \
    rm -rf /app/wheels

USER appuser

# Punto de entrada unificado usando la interfaz CLI (cli.py) de tu ecosistema
ENTRYPOINT ["python", "gema_orquestador/cli.py"]
