"""Caso real: do evento na câmera à decisão humana registrada com cadeia de custódia.

Fluxo: vídeo -> intrusão detectada na borda -> alerta enviado à API -> operador faz
login -> revisa e escala -> evidência (frame com rostos borrados) é enviada e tem a
integridade verificada -> cadeia Merkle do log forense é conferida.

A API roda em processo (FastAPI TestClient, sem abrir porta). O operador de
demonstração usa uma senha aleatória gerada em memória (nunca impressa).

Uso:
    python examples/04_fluxo_hitl_completo/run.py
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
from _comum import argumentos, executar, imprimir, preparar_video

from src.edge.analytics import Schedule, ZoneIntrusionDetector
from src.edge.processor import EdgeAIProcessor


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = argumentos(__doc__.splitlines()[0], "intrusao", "2026-11-22T23:10:00").parse_args(argv)
    saida = Path(args.saida)
    os.environ.setdefault("DATABASE_URL", "")  # SQLite local se nada configurado
    os.environ["EVIDENCE_DIR"] = str(saida / "evidencias")

    # 1) Borda: detecção de intrusão com rostos borrados (Haar) no frame salvo
    video = preparar_video(args.video, "intrusao", saida)
    detector = ZoneIntrusionDetector(
        zone=[(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)],
        schedule=Schedule.from_config([("19:00", "07:00")]),
        zone_name="almoxarifado",
    )
    processor = EdgeAIProcessor(backend="haar", device="CPU")
    resumo, forense = executar("CAM-ALMOX", [detector], video, args.inicio, saida, True, processor)
    if not resumo.events:
        raise SystemExit("Nenhuma intrusão detectada; nada a revisar")
    evento = resumo.events[0]
    snapshot = next((saida / "snapshots").glob(f"{evento.frame_index:05d}_*.jpg"))

    # 2) Nuvem: API real com um operador de demonstração (hash PBKDF2 em memória)
    from fastapi.testclient import TestClient

    from src.cloud.api.middleware import auth
    from src.hitl.dashboard_server import app

    senha = secrets.token_urlsafe(16)
    auth.operator_auth._users = {
        "operador.demo": {"role": "operator", "password_hash": auth.hash_password(senha, iterations=50_000)}
    }

    with TestClient(app) as api:
        token = api.post("/api/v1/auth/token", data={"username": "operador.demo", "password": senha})
        token.raise_for_status()
        api.headers["Authorization"] = f"Bearer {token.json()['access_token']}"

        alerta = api.post(
            "/api/v1/alerts/",
            json={
                "camera_id": evento.camera_id,
                "alarm_score": evento.alarm_score,
                "behavior_indicators": [evento.type],
                "metadata": {"evento_borda": evento.id, "zona": evento.details["zone"]},
            },
        )
        alerta.raise_for_status()
        alerta_id = alerta.json()["alert_id"]

        evidencia = api.post(
            f"/api/v1/evidence/upload?alert_id={alerta_id}&camera_id={evento.camera_id}",
            files={"file": (snapshot.name, snapshot.read_bytes(), "image/jpeg")},
        )
        evidencia.raise_for_status()
        evidencia_id = evidencia.json()["evidence_id"]

        decisao = api.post(
            "/api/v1/hitl/review",
            json={"alert_id": alerta_id, "decision": "escalate", "justification": "Pessoa no almoxarifado às 23h"},
        )
        decisao.raise_for_status()

        verificacao = api.post(f"/api/v1/evidence/{evidencia_id}/verify").json()
        estado_final = api.get(f"/api/v1/alerts/{alerta_id}").json()["status"]

    # 3) Cadeia de custódia do log da borda
    from src.forensic.logger import ForensicLogger

    batch_files = sorted((forense / "archives").glob("*.json"))
    cadeia_ok = None
    if batch_files:
        import json

        batch = json.loads(batch_files[-1].read_text(encoding="utf-8"))
        cadeia_ok = ForensicLogger(log_dir=str(forense), tsa_enabled=False).verify_evidence_chain(evento.id, batch)[
            "valid"
        ]

    resultado = {
        "cenario": "fluxo_hitl_completo",
        "evento_borda": evento.to_evidence(),
        "alerta_id": alerta_id,
        "status_inicial_alerta": alerta.json()["status"],
        "decisao_operador": decisao.json()["decision"],
        "operador_registrado": decisao.json()["operator_id"],
        "status_final_alerta": estado_final,
        "evidencia_integra": verificacao.get("verified"),
        "cadeia_merkle_valida": cadeia_ok,
        "snapshot_com_rostos_borrados": str(snapshot),
        "frame_shape": list(cv2.imread(str(snapshot)).shape),
    }
    imprimir(resultado)
    return resultado


if __name__ == "__main__":
    main()
