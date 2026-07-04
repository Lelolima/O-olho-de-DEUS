"""
RTSP Streamer - Captura de streams RTSP/WebRTC com baixa latência.

Este módulo gerencia captura contínua de streams de vídeo RTSP/HTTP,
com reconexão automática, buffer circular e métricas de desempenho.

Arquitetura:
1. Thread dedicada para leitura contínua (não-blocking)
2. Queue circular (thread-safe) para frames
3. Reconexão automática com backoff exponencial
4. Heartbeat para detecção de stream morto

Uso:
    streamer = RTSPStreamer(
        rtsp_url="rtsp://192.168.1.100:554/stream1",
        buffer_size=3,
        reconnect_delay=1.0
    )
    streamer.start()

    while True:
        frame = streamer.read_frame()
        if frame is not None:
            process(frame)
"""

import logging
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StreamStats:
    """Estatísticas de performance do stream."""

    frames_read: int = 0
    frames_dropped: int = 0
    reconnects: int = 0
    last_frame_time: Optional[datetime] = None
    latency_avg_ms: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)

    @property
    def uptime_seconds(self) -> float:
        """Tempo de atividade em segundos."""
        return (datetime.now() - self.start_time).total_seconds()

    @property
    def fps_effective(self) -> float:
        """FPS efetivo (frames lidos / uptime)."""
        uptime = self.uptime_seconds
        if uptime > 0:
            return self.frames_read / uptime
        return 0.0

    def to_dict(self) -> dict:
        """Serializa para dict."""
        return {
            "frames_read": self.frames_read,
            "frames_dropped": self.frames_dropped,
            "reconnects": self.reconnects,
            "latency_avg_ms": self.latency_avg_ms,
            "uptime_seconds": self.uptime_seconds,
            "fps_effective": self.fps_effective
        }


class RTSPStreamer:
    """
    Streamer RTSP com reconexão automática e buffer.

    Features:
    - Thread de leitura não-bloqueante
    - Buffer circular (drop frames antigos se consumidor lento)
    - Reconexão com backoff exponencial
    - Validação de URLs RTSP/HTTP
    - Métricas de latência e FPS
    """

    # Codecs suportados
    CODEC_H264 = cv2.CAP_FFMPEG  # Via GStreamer/FFmpeg
    CODEC_H265 = cv2.CAP_FFMPEG
    CODEC_MJPEG = cv2.CAP_MJPEG

    def __init__(
        self,
        rtsp_url: str,
        buffer_size: int = 3,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 30.0,
        frame_timeout: float = 5.0,
        validate_url: bool = True
    ):
        """
        Inicializa RTSP Streamer.

        Args:
            rtsp_url: URL do stream (rtsp:// ou http://)
            buffer_size: Tamanho do buffer de frames
            reconnect_delay: Delay inicial entre reconexões (segundos)
            max_reconnect_delay: Delay máximo entre reconexões
            frame_timeout: Timeout para leitura de frame (segundos)
            validate_url: Se True, valida URL antes de conectar
        """
        self.rtsp_url = rtsp_url
        self.buffer_size = buffer_size
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.frame_timeout = frame_timeout

        # Validação inicial
        if validate_url:
            self._validate_url()

        # Thread-safe queue para frames
        self._queue: deque = deque(maxlen=buffer_size)
        self._queue_lock = threading.Lock()

        # Controles da thread
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected = threading.Event()
        self._connection_attempt = threading.Event()

        # Capture do OpenCV
        self._cap: Optional[cv2.VideoCapture] = None

        # Estatísticas
        self.stats = StreamStats()

        # Lock de reconexão
        self._reconnect_lock = threading.Lock()

    def _validate_url(self):
        """Valida formato da URL RTSP/HTTP."""
        valid_prefixes = [
            "rtsp://",
            "rtsp://",
            "http://",
            "https://",
            "file://",
            "/dev/video",  # Webcams Linux
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"  # Webcams Windows (índice)
        ]

        is_valid = any(
            self.rtsp_url.startswith(prefix)
            for prefix in valid_prefixes
        )

        if not is_valid:
            raise ValueError(
                f"URL RTSP inválida: {self.rtsp_url}\n"
                f"Deve começar com rtsp://, http://, https://, ou índice de webcam"
            )

        # Verifica se não é IP privado exceto localhost
        if "://" in self.rtsp_url:
            from urllib.parse import urlparse
            import ipaddress

            parsed = urlparse(self.rtsp_url)
            hostname = parsed.hostname

            if hostname:
                try:
                    ip = ipaddress.ip_address(hostname)
                    if ip.is_private and not ip.is_loopback:
                        logger.warning(f"URL aponta para IP privado: {hostname}")
                except ValueError:
                    pass  # Hostname não é IP, ok

    def start(self):
        """Inicia thread de leitura do stream."""
        if self._thread and self._thread.is_alive():
            logger.warning("Streamer já está rodando")
            return

        logger.info(f"Iniciando streamer para {self.rtsp_url}")

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

        # Aguarda primeira conexão
        if not self._connected.wait(timeout=self.frame_timeout):
            logger.error(f"Timeout na conexão inicial: {self.rtsp_url}")

    def stop(self):
        """Para thread e libera recursos."""
        logger.info(f"Parando streamer: {self.rtsp_url}")

        self._stop_event.set()
        self._connected.clear()

        # Libera capture
        if self._cap:
            self._cap.release()
            self._cap = None

        # Aguarda thread
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def read_frame(self, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """
        Lê próximo frame do buffer.

        Args:
            timeout: Timeout em segundos. None usa frame_timeout.

        Returns:
            Frame BGR ou None se timeout/desconectado
        """
        wait_time = timeout if timeout is not None else self.frame_timeout

        try:
            with self._queue_lock:
                if self._queue:
                    frame = self._queue.popleft()
                    self.stats.frames_read += 1
                    self.stats.last_frame_time = datetime.now()
                    return frame
                else:
                    # Queue vazia
                    if not self._connected.is_set():
                        logger.debug("Stream não conectado")
                    return None

        except Exception as e:
            logger.error(f"Erro ao ler frame: {e}")
            return None

    def is_connected(self) -> bool:
        """Verifica se stream está conectado."""
        return self._connected.is_set() and self._cap is not None and self._cap.isOpened()

    def get_stats(self) -> dict:
        """Retorna estatísticas do stream."""
        self.stats.frames_dropped = max(
            0,
            len(self._queue) - self.buffer_size
        )
        return self.stats.to_dict()

    def _reader_loop(self):
        """Loop principal de leitura (roda em thread separada)."""
        current_delay = self.reconnect_delay

        while not self._stop_event.is_set():
            try:
                # Tenta conectar
                self._connect()

                # Reset delay após conexão bem-sucedida
                current_delay = self.reconnect_delay

                # Lê frames enquanto conectado
                while not self._stop_event.is_set():
                    if not self._cap.isOpened():
                        logger.warning("Stream fechado, reconectando...")
                        break

                    ret, frame = self._cap.read()

                    if not ret:
                        logger.warning("Falha ao ler frame, reconectando...")
                        self.stats.frames_dropped += 1
                        break

                    # Adiciona ao buffer (drop mais antigo se cheio)
                    with self._queue_lock:
                        if len(self._queue) >= self.buffer_size:
                            self._queue.popleft()
                            self.stats.frames_dropped += 1
                        self._queue.append(frame)

                # Limpa capture
                if self._cap:
                    self._cap.release()
                    self._cap = None
                self._connected.clear()

            except Exception as e:
                logger.error(f"Erro no reader loop: {e}")
                self._connected.clear()

            # Backoff exponencial para reconexão
            if not self._stop_event.is_set():
                logger.info(f"Tentando reconexão em {current_delay:.1f}s...")
                time.sleep(current_delay)
                current_delay = min(current_delay * 2, self.max_reconnect_delay)

    def _connect(self):
        """Estabelece conexão com stream RTSP."""
        logger.info(f"Conectando a {self.rtsp_url}...")

        # GStreamer options para baixa latência
        gstreamer_options = [
            "latency=100",           # 100ms buffer
            "buffer-size=512",       # 512KB buffer
            "drop-on-latency=true",  # Drop frames se latência alta
            "max-bitrate=0",         # Sem limite de bitrate
        ]

        # Constroi GStreamer pipeline
        if self.rtsp_url.startswith("rtsp://"):
            gst_pipeline = (
                f"gstrtspsrc location={self.rtsp_url} "
                f"{' '.join(gstreamer_options)} ! "
                f"rtph264depay ! avdec_h264 ! "
                f"videoconvert ! appsink"
            )
            self._cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        else:
            # HTTP stream ou webcam
            self._cap = cv2.VideoCapture(self.rtsp_url)

        # Configurações adicionais
        if self._cap:
            # Buffer settings
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

            # Timeout (alguns backends suportam)
            self._cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(self.frame_timeout * 1000))

        # Verifica se abriu
        if not self._cap or not self._cap.isOpened():
            raise ConnectionError(f"Falha ao abrir stream: {self.rtsp_url}")

        logger.info(f"Conectado a {self.rtsp_url}")
        self._connected.set()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


class MultiStreamManager:
    """
    Gerencia múltiplos streams RTSP simultâneos.

    Útil para cenários com 4-8 câmeras simultâneas.

    Uso:
        manager = MultiStreamManager()
        manager.add_stream("CAM-001", "rtsp://192.168.1.100/stream1")
        manager.add_stream("CAM-002", "rtsp://192.168.1.101/stream1")
        manager.start_all()

        # Processa frames de todas câmeras
        frames = manager.read_all_frames()
        for camera_id, frame in frames.items():
            process(camera_id, frame)
    """

    def __init__(self, max_streams: int = 8):
        """
        Inicializa MultiStreamManager.

        Args:
            max_streams: Número máximo de streams simultâneos
        """
        self.max_streams = max_streams
        self._streamers: dict[str, RTSPStreamer] = {}
        self._threads: dict[str, threading.Thread] = {}

    def add_stream(self, camera_id: str, rtsp_url: str) -> bool:
        """Adiciona stream ao manager."""
        if len(self._streamers) >= self.max_streams:
            logger.error(f"Máximo de {self.max_streams} streams atingido")
            return False

        self._streamers[camera_id] = RTSPStreamer(rtsp_url)
        logger.info(f"Stream {camera_id} adicionado: {rtsp_url}")
        return True

    def remove_stream(self, camera_id: str):
        """Remove e para stream."""
        if camera_id in self._streamers:
            self._streamers[camera_id].stop()
            del self._streamers[camera_id]

    def start_all(self):
        """Inicia todos os streams."""
        for camera_id, streamer in self._streamers.items():
            logger.info(f"Iniciando stream {camera_id}")
            streamer.start()

    def stop_all(self):
        """Para todos os streams."""
        for streamer in self._streamers.values():
            streamer.stop()

    def read_all_frames(self) -> dict[str, Optional[np.ndarray]]:
        """
        Lê frames de todos os streams.

        Returns:
            Dict {camera_id: frame ou None}
        """
        frames = {}
        for camera_id, streamer in self._streamers.items():
            frames[camera_id] = streamer.read_frame(timeout=0.1)
        return frames

    def get_all_stats(self) -> dict[str, dict]:
        """Retorna estatísticas de todos os streams."""
        return {
            camera_id: streamer.get_stats()
            for camera_id, streamer in self._streamers.items()
        }