# Dockerfile Edge AI
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar pyproject.toml
COPY pyproject.toml .

# Instalar Poetry e dependências
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --extras edge --no-interaction

# Copiar código
COPY src/ ./src/
COPY main.py .
COPY config.yaml.example config.yaml

# Expor porta da API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Comando
CMD ["python", "main.py", "--config", "config.yaml", "--mode", "all"]