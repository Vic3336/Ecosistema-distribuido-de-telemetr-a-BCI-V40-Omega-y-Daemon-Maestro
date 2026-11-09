FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
# Si tienes más código fuente, asegúrate de copiarlo también:
COPY . .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install .

# Comando con el que arrancará tu daemon maestro o script principal
CMD ["python", "daemon.py"]
