"""Pipeline de processamento na borda: frame → detecções → eventos → log forense.

Este é o caminho usado por ``python main.py --mode edge`` e pelos exemplos em
``examples/``. Ele é síncrono e determinístico: para arquivos de vídeo cada frame é
processado (nenhum é descartado) e o horário de cada frame é derivado do FPS,
o que permite reproduzir cenários (ex.: intrusão fora do horário) em testes.

Privacidade: os rostos são borrados no frame de saída e **embeddings faciais não
são gravados** na evidência forense — apenas contagem e caixas delimitadoras.
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol

import numpy as np

from src.edge.sources import is_file_source, open_capture, parse_source

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Evento produzido por um analisador (intrusão, contagem, objeto abandonado...)."""

    type: str
    camera_id: str
    timestamp: datetime
    frame_index: int
    alarm_score: float
    details: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")

    def to_evidence(self) -> dict[str, Any]:
        """Formato aceito por :meth:`ForensicLogger.log_evidence`."""
        return {
            "id": self.id,
            "type": self.type,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "frame_index": self.frame_index,
            "alarm_score": round(float(self.alarm_score), 4),
            "details": self.details,
        }


class Analyzer(Protocol):
    """Interface dos analisadores de vídeo."""

    name: str

    def process(self, frame: np.ndarray, timestamp: datetime, frame_index: int) -> list[Event]: ...


@dataclass
class PipelineSummary:
    frames_processed: int = 0
    faces_detected: int = 0
    events: list[Event] = field(default_factory=list)
    batches_flushed: int = 0

    @property
    def events_by_type(self) -> dict[str, int]:
        return dict(Counter(e.type for e in self.events))

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames_processed": self.frames_processed,
            "faces_detected": self.faces_detected,
            "events": len(self.events),
            "events_by_type": self.events_by_type,
            "batches_flushed": self.batches_flushed,
        }


class VideoPipeline:
    """Orquestra detecção facial (opcional), analisadores e log forense."""

    def __init__(
        self,
        camera_id: str,
        analyzers: Sequence[Analyzer] = (),
        processor: Any | None = None,
        forensic_logger: Any | None = None,
        face_event_min_faces: int = 0,
        on_event: Callable[[Event], None] | None = None,
    ) -> None:
        """
        Args:
            camera_id: Identificador da câmera.
            analyzers: Analisadores aplicados a cada frame.
            processor: ``EdgeAIProcessor`` (detecção facial + blur); ``None`` desliga.
            forensic_logger: ``ForensicLogger``; cada evento vira evidência encadeada.
            face_event_min_faces: Se > 0, gera evento ``faces_detected`` quando houver
                pelo menos essa quantidade de rostos no frame.
            on_event: Callback chamado para cada evento (ex.: enviar à API).
        """
        self.camera_id = camera_id
        self.analyzers = list(analyzers)
        self.processor = processor
        self.forensic_logger = forensic_logger
        self.face_event_min_faces = face_event_min_faces
        self.on_event = on_event
        self.last_masked_frame: np.ndarray | None = None

    def process_frame(self, frame: np.ndarray, timestamp: datetime, frame_index: int) -> tuple[list[Event], int]:
        """Processa um frame; retorna (eventos, número de rostos)."""
        events: list[Event] = []
        faces_count = 0

        if self.processor is not None:
            faces, masked = self.processor.process_frame(frame, extract_embedding=False)
            self.last_masked_frame = masked
            faces_count = len(faces)
            if self.face_event_min_faces and faces_count >= self.face_event_min_faces:
                events.append(
                    Event(
                        type="faces_detected",
                        camera_id=self.camera_id,
                        timestamp=timestamp,
                        frame_index=frame_index,
                        alarm_score=min(1.0, 0.3 + 0.1 * faces_count),
                        details={
                            "faces_count": faces_count,
                            "bounding_boxes": [list(map(int, f.bounding_box)) for f in faces],
                        },
                    )
                )

        for analyzer in self.analyzers:
            for event in analyzer.process(frame, timestamp, frame_index):
                event.camera_id = self.camera_id
                events.append(event)

        for event in events:
            if self.forensic_logger is not None:
                self.forensic_logger.log_evidence(event.to_evidence())
            if self.on_event is not None:
                self.on_event(event)
            logger.info(f"[{self.camera_id}] {event.type} (score={event.alarm_score:.2f}) frame={frame_index}")

        return events, faces_count

    def run_frames(
        self,
        frames: Iterable[np.ndarray],
        fps: float,
        start_time: datetime,
        max_frames: int | None = None,
    ) -> PipelineSummary:
        """Processa uma sequência de frames (útil para testes e fontes customizadas)."""
        summary = PipelineSummary()
        step = timedelta(seconds=1.0 / fps if fps > 0 else 0.0)
        for index, frame in enumerate(frames):
            if max_frames is not None and index >= max_frames:
                break
            events, faces = self.process_frame(frame, start_time + step * index, index)
            summary.frames_processed += 1
            summary.faces_detected += faces
            summary.events.extend(events)
        if self.forensic_logger is not None and self.forensic_logger.flush_batch():
            summary.batches_flushed += 1
        return summary

    def run(
        self,
        source: str | int,
        max_frames: int | None = None,
        start_time: datetime | None = None,
        default_fps: float = 25.0,
    ) -> PipelineSummary:
        """Lê a fonte até o fim (arquivo) ou até ``max_frames``.

        Para arquivos, o horário do frame é ``start_time + índice / FPS`` (``start_time``
        padrão: agora). Para câmeras ao vivo é o relógio local.
        """
        target = parse_source(source)
        cap = open_capture(target)
        live = not is_file_source(target)
        fps = cap.get(5) or default_fps  # cv2.CAP_PROP_FPS == 5
        if fps <= 0 or fps > 240:
            fps = default_fps
        start = start_time or datetime.now().astimezone()

        def frames() -> Iterable[np.ndarray]:
            while True:
                ok, frame = cap.read()
                if not ok:
                    return
                yield frame

        try:
            if live:
                summary = PipelineSummary()
                for index, frame in enumerate(frames()):
                    if max_frames is not None and index >= max_frames:
                        break
                    events, faces = self.process_frame(frame, datetime.now().astimezone(), index)
                    summary.frames_processed += 1
                    summary.faces_detected += faces
                    summary.events.extend(events)
                if self.forensic_logger is not None and self.forensic_logger.flush_batch():
                    summary.batches_flushed += 1
                return summary
            return self.run_frames(frames(), fps=fps, start_time=start, max_frames=max_frames)
        finally:
            cap.release()
