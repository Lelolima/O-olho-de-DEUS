"""Caso real: contagem de entradas/saídas por linha virtual e alerta de lotação.

Uso:
    python examples/02_contagem_de_pessoas/run.py                       # cena sintética
    python examples/02_contagem_de_pessoas/run.py --lotacao 1
    python examples/02_contagem_de_pessoas/run.py --video vtest.avi --detector hog --hog-resize 1.5
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _comum import argumentos, executar, imprimir, preparar_video

from src.edge.analytics import PeopleCounter

# Linha vertical no meio da imagem; "entrada" = movimento da esquerda para a direita
LINHA_PORTA = ((0.5, 0.0), (0.5, 1.0))


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argumentos(__doc__.splitlines()[1], "contagem", "2026-11-22T09:00:00")
    parser.add_argument("--lotacao", type=int, default=2, help="lotação máxima antes do alerta")
    parser.add_argument("--detector", choices=["motion", "hog"], default="motion")
    parser.add_argument("--hog-resize", type=float, default=1.0, help="ampliação para o detector HOG")
    args = parser.parse_args(argv)
    saida = Path(args.saida)
    video = preparar_video(args.video, "contagem", saida)

    contador = PeopleCounter(
        line=LINHA_PORTA,
        detector=args.detector,
        max_occupancy=args.lotacao,
        hog_resize=args.hog_resize,
    )
    resumo, forense = executar("CAM-PORTA", [contador], video, args.inicio, saida, not args.sem_snapshots)
    resultado = {
        "cenario": "contagem_de_pessoas",
        "detector": args.detector,
        "entradas": contador.entries,
        "saidas": contador.exits,
        "ocupacao_final": contador.occupancy,
        "lotacao_maxima": args.lotacao,
        **resumo.to_dict(),
        "eventos": [e.to_evidence() for e in resumo.events],
        "log_forense": str(forense),
    }
    imprimir(resultado)
    return resultado


if __name__ == "__main__":
    main()
