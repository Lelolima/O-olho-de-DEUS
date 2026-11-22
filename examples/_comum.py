"""Utilidades compartilhadas pelos exemplos (não faz parte da API do pacote)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import cv2  # noqa: E402

from src.edge.pipeline import Event, PipelineSummary, VideoPipeline  # noqa: E402
from src.forensic.logger import ForensicLogger  # noqa: E402
from src.tools.sample_videos import make_scene  # noqa: E402


def argumentos(descricao: str, cena: str, inicio_padrao: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument("--video", help=f"vídeo de entrada (padrão: gera a cena sintética '{cena}')")
    parser.add_argument("--inicio", default=inicio_padrao, help="data/hora do 1º frame, ISO 8601")
    parser.add_argument("--saida", default="saida_exemplo", help="pasta para logs forenses e snapshots")
    parser.add_argument("--sem-snapshots", action="store_true", help="não salvar imagens dos eventos")
    return parser


def preparar_video(video: str | None, cena: str, saida: Path) -> str:
    if video:
        return video
    return str(make_scene(cena, saida / f"{cena}_sintetico.avi"))


def executar(
    camera_id: str,
    analisadores: list[Any],
    video: str,
    inicio: str,
    saida: Path,
    snapshots: bool = True,
    processor: Any | None = None,
) -> tuple[PipelineSummary, Path]:
    """Roda o pipeline real com log forense encadeado e (opcional) snapshots."""
    pasta_forense = saida / "forense"
    logger = ForensicLogger(log_dir=str(pasta_forense), tsa_enabled=False, batch_size=50)
    pipeline = VideoPipeline(camera_id, analyzers=analisadores, processor=processor, forensic_logger=logger)
    pasta_snap = saida / "snapshots"

    def salvar(evento: Event) -> None:
        if not snapshots or pipeline.current_frame is None:
            return
        img = pipeline.current_frame.copy()
        caixas = evento.details.get("boxes") or ([evento.details["box"]] if "box" in evento.details else [])
        for x, y, w, h in caixas:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.putText(img, evento.type, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        pasta_snap.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(pasta_snap / f"{evento.frame_index:05d}_{evento.type}.jpg"), img)

    pipeline.on_event = salvar
    resumo = pipeline.run(video, start_time=datetime.fromisoformat(inicio))
    return resumo, pasta_forense


def imprimir(resultado: dict[str, Any]) -> None:
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
