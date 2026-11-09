FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY . .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install .

# Comando de arranque apuntando al daemon maestro
CMD ["python", "daemon.py"]
