# Usamos una imagen oficial de Python con soporte moderno
FROM python:3.11-slim

WORKDIR /app

# Copias el pyproject.toml y dejas que pip lo lea de forma nativa
COPY pyproject.toml .

RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -e .
    
