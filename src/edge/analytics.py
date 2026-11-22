"""Analisadores de vídeo para casos reais de segurança (CPU, sem downloads).

Todos implementam ``process(frame, timestamp, frame_index) -> list[Event]`` e são
usados pelo :class:`src.edge.pipeline.VideoPipeline`.

- :class:`ZoneIntrusionDetector` — movimento dentro de um polígono, opcionalmente
  só em janelas de horário (ex.: fora do expediente).
- :class:`PeopleCounter` — contagem por cruzamento de linha virtual (entradas/saídas)
  e alerta de lotação. Detecção por blobs de movimento (padrão) ou pelo detector
  HOG de pessoas embutido no OpenCV.
- :class:`AbandonedObjectDetector` — região que passa a diferir do fundo e fica
  parada por mais de N segundos (objeto deixado para trás).

Coordenadas de zonas e linhas são **normalizadas** (0–1, relativas à largura/altura
do frame), o que torna a configuração independente da resolução da câmera.

Nada aqui identifica pessoas: não há reconhecimento facial nem biometria.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

import cv2
import numpy as np

from src.edge.pipeline import Event

Point = tuple[float, float]
Box = tuple[int, int, int, int]  # x, y, w, h


# --------------------------------------------------------------------------- utilidades


def parse_hhmm(value: str) -> time:
    hours, minutes = value.strip().split(":")
    return time(int(hours), int(minutes))


@dataclass
class Schedule:
    """Janelas de horário em que o analisador fica ativo; vazio = sempre ativo.

    Janelas que atravessam a meia-noite são suportadas: ``("19:00", "07:00")``.
    """

    windows: list[tuple[time, time]] = field(default_factory=list)

    @classmethod
    def from_config(cls, windows: Iterable[Sequence[str]] | None) -> Schedule:
        return cls([(parse_hhmm(a), parse_hhmm(b)) for a, b in (windows or [])])

    def is_active(self, moment: datetime) -> bool:
        if not self.windows:
            return True
        now = moment.time().replace(tzinfo=None)
        for start, end in self.windows:
            if start <= end:
                if start <= now < end:
                    return True
            elif now >= start or now < end:  # atravessa a meia-noite
                return True
        return False


def to_pixels(points: Sequence[Point], shape: tuple[int, ...]) -> np.ndarray:
    h, w = shape[:2]
    return np.array([[round(x * w), round(y * h)] for x, y in points], dtype=np.int32)


def box_center(box: Box) -> tuple[float, float]:
    x, y, w, h = box
    return x + w / 2.0, y + h / 2.0


def box_iou(a: Box, b: Box) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


class MotionBlobDetector:
    """Blobs de primeiro plano via subtração de fundo MOG2."""

    def __init__(self, min_area_ratio: float = 0.002, history: int = 300, var_threshold: float = 25.0) -> None:
        self.min_area_ratio = min_area_ratio
        self._subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=var_threshold, detectShadows=False
        )
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def detect(self, frame: np.ndarray) -> list[Box]:
        mask = self._subtractor.apply(frame)
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel, iterations=2)
        min_area = self.min_area_ratio * frame.shape[0] * frame.shape[1]
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: list[Box] = []
        for c in contours:
            if cv2.contourArea(c) >= min_area:
                x, y, w, h = cv2.boundingRect(c)
                boxes.append((int(x), int(y), int(w), int(h)))
        return boxes


class HogPersonDetector:
    """Detector de pessoas HOG + SVM linear que acompanha o OpenCV (sem download).

    A janela do HOG tem 64x128 px: pessoas menores que ~128 px de altura não são
    detectadas. Use ``resize`` > 1 para câmeras distantes (custa CPU: no vídeo de
    teste 768x576, 1.0 ≈ 0,13 s/frame e 1.5 ≈ 0,34 s/frame).
    """

    def __init__(self, resize: float = 1.0, min_weight: float = 0.3) -> None:
        if resize <= 0:
            raise ValueError("resize deve ser > 0")
        self.resize = resize
        self.min_weight = min_weight
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(np.asarray(cv2.HOGDescriptor.getDefaultPeopleDetector(), dtype=np.float32))

    def detect(self, frame: np.ndarray) -> list[Box]:
        scale = self.resize
        img = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
        rects, weights = self._hog.detectMultiScale(img, winStride=(8, 8), padding=(8, 8), scale=1.05)
        boxes: list[Box] = []
        for (x, y, w, h), weight in zip(rects, np.ravel(weights), strict=False):
            if float(weight) < self.min_weight:
                continue
            boxes.append((int(x / scale), int(y / scale), int(w / scale), int(h / scale)))
        return _non_max_suppression(boxes, 0.4)


def _overlap_min(a: Box, b: Box) -> float:
    """Interseção dividida pela área da menor caixa (1.0 = uma contém a outra)."""
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    smaller = min(a[2] * a[3], b[2] * b[3])
    return (ix * iy) / smaller if smaller else 0.0


def _non_max_suppression(boxes: list[Box], iou_threshold: float, containment: float = 0.7) -> list[Box]:
    """Mantém as caixas menores (mais justas) e descarta as que se sobrepõem/contêm."""
    kept: list[Box] = []
    for box in sorted(boxes, key=lambda b: b[2] * b[3]):
        if all(box_iou(box, k) < iou_threshold and _overlap_min(box, k) < containment for k in kept):
            kept.append(box)
    return kept


# --------------------------------------------------------------------------- intrusão


class ZoneIntrusionDetector:
    """Alerta quando há movimento dentro de uma zona poligonal no horário ativo."""

    name = "zone_intrusion"

    def __init__(
        self,
        zone: Sequence[Point],
        schedule: Schedule | None = None,
        zone_name: str = "zona",
        min_area_ratio: float = 0.002,
        cooldown_seconds: float = 30.0,
        warmup_frames: int = 10,
        alarm_score: float = 0.8,
    ) -> None:
        if len(zone) < 3:
            raise ValueError("A zona precisa de pelo menos 3 pontos")
        self.zone = list(zone)
        self.schedule = schedule or Schedule()
        self.zone_name = zone_name
        self.cooldown_seconds = cooldown_seconds
        self.warmup_frames = warmup_frames
        self.alarm_score = alarm_score
        self._detector = MotionBlobDetector(min_area_ratio=min_area_ratio)
        self._last_alert: datetime | None = None
        self._seen = 0

    def process(self, frame: np.ndarray, timestamp: datetime, frame_index: int) -> list[Event]:
        boxes = self._detector.detect(frame)  # sempre alimenta o modelo de fundo
        self._seen += 1
        if self._seen <= self.warmup_frames or not self.schedule.is_active(timestamp):
            return []
        polygon = to_pixels(self.zone, frame.shape)
        inside = [b for b in boxes if cv2.pointPolygonTest(polygon, box_center(b), False) >= 0]
        if not inside:
            return []
        if self._last_alert and (timestamp - self._last_alert).total_seconds() < self.cooldown_seconds:
            return []
        self._last_alert = timestamp
        return [
            Event(
                type="zone_intrusion",
                camera_id="",
                timestamp=timestamp,
                frame_index=frame_index,
                alarm_score=self.alarm_score,
                details={"zone": self.zone_name, "objects": len(inside), "boxes": [list(b) for b in inside]},
            )
        ]


# --------------------------------------------------------------------------- contagem


@dataclass
class _Track:
    track_id: int
    center: tuple[float, float]
    side: int  # lado estável (só muda após sair da margem em torno da linha)
    last_frame: int


class PeopleCounter:
    """Conta cruzamentos de uma linha virtual e alerta lotação acima do limite.

    Direção: com a linha definida de cima para baixo (``line[0]`` acima de
    ``line[1]``), "entrada" é o movimento da esquerda para a direita na imagem.
    Troque a ordem dos pontos para inverter.
    """

    name = "people_counter"

    def __init__(
        self,
        line: tuple[Point, Point],
        detector: str = "motion",
        min_area_ratio: float = 0.002,
        max_occupancy: int | None = None,
        max_match_distance: float = 0.12,
        line_margin: float = 0.02,
        max_missed_frames: int = 10,
        warmup_frames: int = 5,
        hog_resize: float = 1.0,
    ) -> None:
        self.line = line
        self.max_occupancy = max_occupancy
        self.max_match_distance = max_match_distance
        self.line_margin = line_margin
        self.max_missed_frames = max_missed_frames
        self.warmup_frames = warmup_frames
        if detector == "hog":
            self._detector: MotionBlobDetector | HogPersonDetector = HogPersonDetector(resize=hog_resize)
        elif detector == "motion":
            self._detector = MotionBlobDetector(min_area_ratio=min_area_ratio)
        else:
            raise ValueError(f"Detector desconhecido: {detector} (use 'motion' ou 'hog')")
        self.detector_name = detector
        self.entries = 0
        self.exits = 0
        self._tracks: list[_Track] = []
        self._next_id = 1
        self._seen = 0
        self._occupancy_alerted = False

    @property
    def occupancy(self) -> int:
        return max(0, self.entries - self.exits)

    def _signed_distance(self, point: tuple[float, float], shape: tuple[int, ...]) -> float:
        """Distância com sinal (pixels) do ponto à linha; o sinal indica o lado."""
        (x1, y1), (x2, y2) = to_pixels(self.line, shape)
        length = math.hypot(x2 - x1, y2 - y1) or 1.0
        return float((x2 - x1) * (point[1] - y1) - (y2 - y1) * (point[0] - x1)) / length

    def process(self, frame: np.ndarray, timestamp: datetime, frame_index: int) -> list[Event]:
        boxes = self._detector.detect(frame)
        self._seen += 1
        if self._seen <= self.warmup_frames:
            return []
        diag = math.hypot(frame.shape[0], frame.shape[1])
        max_dist = self.max_match_distance * diag
        events: list[Event] = []
        unmatched = list(self._tracks)

        margin = self.line_margin * diag
        for box in boxes:
            center = box_center(box)
            distance = self._signed_distance(center, frame.shape)
            best = min(unmatched, key=lambda t: math.dist(t.center, center), default=None)
            if best is None or math.dist(best.center, center) > max_dist:
                side = 1 if distance > 0 else -1
                self._tracks.append(_Track(self._next_id, center, side, frame_index))
                self._next_id += 1
                continue
            unmatched.remove(best)
            # Só considera troca de lado fora da margem (evita contar tremidas na linha)
            if abs(distance) > margin:
                side = 1 if distance > 0 else -1
                if side != best.side:
                    direction = "entrada" if side < 0 else "saida"
                    if direction == "entrada":
                        self.entries += 1
                    else:
                        self.exits += 1
                    events.append(self._event("line_crossing", timestamp, frame_index, 0.2, direction=direction))
                    best.side = side
            best.center, best.last_frame = center, frame_index

        self._tracks = [t for t in self._tracks if frame_index - t.last_frame <= self.max_missed_frames]

        if self.max_occupancy is not None:
            if self.occupancy > self.max_occupancy and not self._occupancy_alerted:
                self._occupancy_alerted = True
                events.append(self._event("occupancy_exceeded", timestamp, frame_index, 0.75))
            elif self.occupancy <= self.max_occupancy:
                self._occupancy_alerted = False
        return events

    def _event(self, kind: str, ts: datetime, idx: int, score: float, **extra: Any) -> Event:
        details: dict[str, Any] = {
            "entries": self.entries,
            "exits": self.exits,
            "occupancy": self.occupancy,
            "detector": self.detector_name,
            **extra,
        }
        if self.max_occupancy is not None:
            details["max_occupancy"] = self.max_occupancy
        return Event(type=kind, camera_id="", timestamp=ts, frame_index=idx, alarm_score=score, details=details)


# --------------------------------------------------------------------------- objeto abandonado


class AbandonedObjectDetector:
    """Detecta regiões novas e paradas (diferentes do fundo) por ``min_static_seconds``.

    Limitação: uma pessoa imóvel pelo mesmo tempo também é sinalizada — por isso o
    alerta vai para revisão humana (HITL) e não para ação automática.
    """

    name = "abandoned_object"

    def __init__(
        self,
        min_static_seconds: float = 30.0,
        min_area_ratio: float = 0.001,
        diff_threshold: int = 35,
        background_frames: int = 10,
        learning_rate: float = 0.001,
        alarm_score: float = 0.75,
    ) -> None:
        self.min_static_seconds = min_static_seconds
        self.min_area_ratio = min_area_ratio
        self.diff_threshold = diff_threshold
        self.background_frames = background_frames
        self.learning_rate = learning_rate
        self.alarm_score = alarm_score
        self._bg_samples: list[np.ndarray] = []
        self._background: np.ndarray | None = None
        self._prev: np.ndarray | None = None
        self._static_since: np.ndarray | None = None
        self._reported: list[Box] = []
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    @staticmethod
    def _gray(frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        return cv2.GaussianBlur(gray, (5, 5), 0).astype(np.float32)

    def process(self, frame: np.ndarray, timestamp: datetime, frame_index: int) -> list[Event]:
        gray = self._gray(frame)
        if self._background is None:
            self._bg_samples.append(gray)
            if len(self._bg_samples) >= self.background_frames:
                self._background = np.median(np.stack(self._bg_samples), axis=0).astype(np.float32)
                self._static_since = np.full(gray.shape, np.nan, dtype=np.float64)
                self._bg_samples.clear()
            self._prev = gray
            return []

        assert self._static_since is not None and self._prev is not None
        foreground = np.abs(gray - self._background) > self.diff_threshold
        moving = cv2.dilate(
            (np.abs(gray - self._prev) > self.diff_threshold / 2).astype(np.uint8), self._kernel, iterations=2
        ).astype(bool)
        static = foreground & ~moving
        self._prev = gray

        now = timestamp.timestamp()
        self._static_since[~static] = np.nan
        newly = static & np.isnan(self._static_since)
        self._static_since[newly] = now

        # Fundo acompanha mudanças lentas de iluminação apenas fora do primeiro plano
        bg_update = ~foreground
        self._background[bg_update] += self.learning_rate * (gray[bg_update] - self._background[bg_update])

        with np.errstate(invalid="ignore"):
            aged = (now - self._static_since) >= self.min_static_seconds
        mask = cv2.morphologyEx(aged.astype(np.uint8) * 255, cv2.MORPH_OPEN, self._kernel)
        min_area = self.min_area_ratio * gray.shape[0] * gray.shape[1]
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        events: list[Event] = []
        fg_boxes: list[Box] = []
        if contours:
            fg_mask = cv2.morphologyEx(foreground.astype(np.uint8) * 255, cv2.MORPH_OPEN, self._kernel)
            fg_contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            fg_boxes = [tuple(int(v) for v in cv2.boundingRect(fc)) for fc in fg_contours]  # type: ignore[misc]
        for c in contours:
            if cv2.contourArea(c) < min_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            box: Box = (int(x), int(y), int(w), int(h))
            # Estende a caixa ao componente de primeiro plano que a contém (o objeto
            # inteiro), pois parte dele pode ter ficado "em movimento" por mais tempo.
            containing = [fb for fb in fg_boxes if _overlap_min(box, fb) > 0.9]
            if containing:
                box = min(containing, key=lambda fb: fb[2] * fb[3])
            if any(box_iou(box, r) > 0.3 for r in self._reported):
                continue
            self._reported.append(box)
            events.append(
                Event(
                    type="abandoned_object",
                    camera_id="",
                    timestamp=timestamp,
                    frame_index=frame_index,
                    alarm_score=self.alarm_score,
                    details={"box": list(box), "static_seconds": self.min_static_seconds},
                )
            )
        return events


# --------------------------------------------------------------------------- configuração


def build_analyzers(config: dict[str, Any] | None) -> list[Any]:
    """Cria analisadores a partir da seção ``analytics`` do config.

    Exemplo (YAML)::

        analytics:
          zone_intrusion:
            zone: [[0.1, 0.1], [0.6, 0.1], [0.6, 0.9], [0.1, 0.9]]
            active_hours: [["19:00", "07:00"]]
          people_counter:
            line: [[0.5, 0.0], [0.5, 1.0]]
            detector: motion        # ou hog
            max_occupancy: 20
          abandoned_object:
            min_static_seconds: 60
    """
    analyzers: list[Any] = []
    if not config:
        return analyzers
    if cfg := config.get("zone_intrusion"):
        analyzers.append(
            ZoneIntrusionDetector(
                zone=[tuple(p) for p in cfg["zone"]],
                schedule=Schedule.from_config(cfg.get("active_hours")),
                zone_name=cfg.get("name", "zona"),
                min_area_ratio=float(cfg.get("min_area_ratio", 0.002)),
                cooldown_seconds=float(cfg.get("cooldown_seconds", 30)),
            )
        )
    if cfg := config.get("people_counter"):
        (ax, ay), (bx, by) = cfg["line"]
        analyzers.append(
            PeopleCounter(
                line=((ax, ay), (bx, by)),
                detector=cfg.get("detector", "motion"),
                min_area_ratio=float(cfg.get("min_area_ratio", 0.002)),
                max_occupancy=cfg.get("max_occupancy"),
                hog_resize=float(cfg.get("hog_resize", 1.0)),
            )
        )
    if cfg := config.get("abandoned_object"):
        analyzers.append(
            AbandonedObjectDetector(
                min_static_seconds=float(cfg.get("min_static_seconds", 30)),
                min_area_ratio=float(cfg.get("min_area_ratio", 0.001)),
            )
        )
    return analyzers
