# Imagem única para os modos api e edge.
# Build:  docker build -f docker/Dockerfile -t olho-de-deus .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# libglib2.0-0: dependência do opencv-python-headless
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY main.py config.yaml.example ./
COPY examples/ ./examples/
RUN cp config.yaml.example config.yaml \
    && useradd --create-home --uid 10001 olho \
    && mkdir -p /app/forensic_logs \
    && chown -R olho /app
USER olho

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

CMD ["python", "main.py", "--config", "config.yaml", "--mode", "api"]
