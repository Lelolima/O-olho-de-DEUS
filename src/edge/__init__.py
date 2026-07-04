"""Edge AI Processing - Captura RTSP, detecção facial e dynamic masking."""

from src.edge.processor import EdgeAIProcessor, FaceDetection, create_processor_from_config
from src.edge.streamer import RTSPStreamer
from src.edge.masker import DynamicMasker  # masker.py ainda não existe, vou cria-lo

__all__ = [
    "EdgeAIProcessor",
    "FaceDetection",
    "RTSPStreamer",
    "DynamicMasker",
    "create_processor_from_config",
]