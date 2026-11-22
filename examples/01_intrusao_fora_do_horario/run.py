"""Caso real: alerta de intrusão em área restrita fora do horário de funcionamento.

Uso:
    python examples/01_intrusao_fora_do_horario/run.py                 # 22:30, gera alerta
    python examples/01_intrusao_fora_do_horario/run.py --inicio 2026-11-22T10:00:00  # expediente
    python examples/01_intrusao_fora_do_horario/run.py --video minha_camera.mp4
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import argumentos, executar, imprimir, preparar_video

from src.edge.analytics import Schedule, ZoneIntrusionDetector

# Metade esquerda da imagem é a área restrita (coordenadas normalizadas 0-1)
ZONA_RESTRITA = [(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)]
FORA_DO_EXPEDIENTE = [("19:00", "07:00")]


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = argumentos(__doc__.splitlines()[1], "intrusao", "2026-11-22T22:30:00").parse_args(argv)
    saida = Path(args.saida)
    video = preparar_video(args.video, "intrusao", saida)

    detector = ZoneIntrusionDetector(
        zone=ZONA_RESTRITA,
        schedule=Schedule.from_config(FORA_DO_EXPEDIENTE),
        zone_name="patio_fundos",
        cooldown_seconds=60,
    )
    resumo, forense = executar("CAM-PATIO", [detector], video, args.inicio, saida, not args.sem_snapshots)
    resultado = {
        "cenario": "intrusao_fora_do_horario",
        "inicio": args.inicio,
        "zona_ativa_no_horario": detector.schedule.is_active(datetime.fromisoformat(args.inicio)),
        **resumo.to_dict(),
        "alertas": [e.to_evidence() for e in resumo.events],
        "log_forense": str(forense),
    }
    imprimir(resultado)
    return resultado


if __name__ == "__main__":
    main()
