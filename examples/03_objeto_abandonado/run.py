"""Caso real: alerta de objeto deixado em área de circulação (ex.: mala no saguão).

Uso:
    python examples/03_objeto_abandonado/run.py                 # alerta após 5 s parado
    python examples/03_objeto_abandonado/run.py --segundos 60   # limiar mais realista
    python examples/03_objeto_abandonado/run.py --video saguao.mp4 --segundos 120
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import argumentos, executar, imprimir, preparar_video

from src.edge.analytics import AbandonedObjectDetector


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argumentos(__doc__.splitlines()[1], "abandono", "2026-11-22T14:00:00")
    parser.add_argument("--segundos", type=float, default=5.0, help="tempo parado até o alerta")
    args = parser.parse_args(argv)
    saida = Path(args.saida)
    video = preparar_video(args.video, "abandono", saida)

    detector = AbandonedObjectDetector(min_static_seconds=args.segundos)
    resumo, forense = executar("CAM-SAGUAO", [detector], video, args.inicio, saida, not args.sem_snapshots)
    resultado = {
        "cenario": "objeto_abandonado",
        "limiar_segundos": args.segundos,
        **resumo.to_dict(),
        "alertas": [e.to_evidence() for e in resumo.events],
        "log_forense": str(forense),
    }
    imprimir(resultado)
    return resultado


if __name__ == "__main__":
    main()
