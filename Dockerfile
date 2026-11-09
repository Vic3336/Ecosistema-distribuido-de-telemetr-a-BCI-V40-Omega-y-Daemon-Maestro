# Copias el pyproject.toml y dejas que pip lo lea de forma nativa si tu versión lo soporta, 
# o aseguras un requirements.txt estático:
COPY pyproject.toml .

RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -e .
    
