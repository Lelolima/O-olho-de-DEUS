"""Abertura de fontes de vídeo (webcam, arquivo, RTSP/HTTP).

Centraliza a regra usada pelo streamer e pelo pipeline:

- ``"0"``, ``"1"``... → índice de webcam (``int``); ``VideoCapture("0")`` tentaria abrir um arquivo.
- caminho existente ou ``file://`` → arquivo de vídeo.
- ``rtsp://``/``rtsps://`` → GStreamer apenas se o OpenCV foi compilado com ele
  (os wheels do PyPI não são); caso contrário FFmpeg.
- ``http(s)://`` → backend padrão (MJPEG/HLS via FFmpeg).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import cv2

logger = logging.getLogger(__name__)

STREAM_SCHEMES = ("rtsp", "rtsps", "http", "https")


class VideoSourceError(ValueError):
    """Fonte de vídeo inválida ou impossível de abrir."""


def parse_source(source: str | int) -> int | str:
    """Normaliza a fonte: índice de webcam vira ``int``; ``file://`` vira caminho."""
    if isinstance(source, int):
        return source
    text = str(source).strip()
    if not text:
        raise VideoSourceError("Fonte de vídeo vazia")
    if text.isdigit():
        return int(text)
    if text.startswith("/dev/video"):
        return text
    parsed = urlparse(text)
    if parsed.scheme == "file":
        text = parsed.path.lstrip("/") if len(parsed.path) > 2 and parsed.path[2] == ":" else parsed.path
    elif parsed.scheme in STREAM_SCHEMES:
        return text
    elif "://" in text:
        raise VideoSourceError(f"Esquema não suportado: {parsed.scheme}://")
    if not Path(text).exists():
        raise VideoSourceError(f"Arquivo de vídeo não encontrado: {text}")
    return text


def is_file_source(source: int | str) -> bool:
    return isinstance(source, str) and urlparse(source).scheme not in STREAM_SCHEMES and Path(source).exists()


@lru_cache(maxsize=1)
def opencv_has_gstreamer() -> bool:
    for line in cv2.getBuildInformation().splitlines():
        if "GStreamer" in line:
            return "YES" in line.upper()
    return False


def open_capture(source: str | int, open_timeout_s: float = 5.0) -> cv2.VideoCapture:
    """Abre ``cv2.VideoCapture`` para a fonte; lança ``VideoSourceError`` se falhar."""
    target = parse_source(source)

    if isinstance(target, str) and target.startswith(("rtsp://", "rtsps://")):
        if opencv_has_gstreamer():
            pipeline = (
                f"rtspsrc location={target} latency=100 drop-on-latency=true ! "
                "decodebin ! videoconvert ! appsink drop=true max-buffers=1"
            )
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        else:
            cap = cv2.VideoCapture(target, cv2.CAP_FFMPEG)
    else:
        cap = cv2.VideoCapture(target)

    if cap is not None and not is_file_source(target):
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(open_timeout_s * 1000))

    if cap is None or not cap.isOpened():
        if cap is not None:
            cap.release()
        raise VideoSourceError(f"Falha ao abrir fonte de vídeo: {redact_url(str(source))}")
    return cap


def redact_url(url: str) -> str:
    """Remove usuário/senha de URLs (ex.: rtsp://user:pass@host) para logs."""
    parsed = urlparse(url)
    if parsed.password or parsed.username:
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc += f":{parsed.port}"
        return parsed._replace(netloc=f"***@{netloc}").geturl()
    return url
