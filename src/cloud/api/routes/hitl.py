"""HITL Routes - API para revisão humana de alertas."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.cloud.api.middleware.auth import authenticate_websocket, get_current_operator
from src.cloud.database import IncidentRepository, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


# === Schemas ===


class HitlReviewRequest(BaseModel):
    """Solicitação de revisão HITL."""

    alert_id: str
    decision: str  # "dismiss" | "escalate" | "request_more_info"
    justification: str | None = Field(None, max_length=500)
    confidence_override: float | None = Field(None, ge=0, le=1)


class HitlDecision(BaseModel):
    """Decisão HITL registrada."""

    decision_id: str
    alert_id: str
    operator_id: str
    decision: str
    justification: str | None
    decided_at: datetime
    alert_score: float
    alert_camera: str


class OperatorStats(BaseModel):
    """Estatísticas do operador."""

    operator_id: str
    total_reviews: int
    dismissals: int
    escalations: int
    avg_decision_time_seconds: float
    escalation_rate: float


# === In-Memory Store ===

_decisions_store: dict[str, dict] = {}
_operator_stats: dict[str, dict] = {}


# === Routes ===


@router.post("/review", response_model=HitlDecision)
async def submit_hitl_review(
    review: HitlReviewRequest,
    operator: dict = Depends(get_current_operator),
    db: Session = Depends(get_db),
):
    """
    Operador submete decisão de revisão HITL.

    Esta decisão é registrada no log forense para audit trail.
    """
    import uuid

    # Antes: operator_id vinha da query string (padrão "anonymous") e qualquer
    # pessoa podia registrar decisões em nome de outra. Agora vem do JWT.
    operator_id = operator["username"]
    decision_id = f"hitl_{uuid.uuid4().hex[:12]}"

    # Alertas criados pela API ficam no banco; o dicionário em memória é só o
    # fallback quando o banco está indisponível. Antes só a memória era consultada,
    # então a revisão nunca encontrava alertas persistidos.
    from src.cloud.api.routes.alerts import _alerts_store

    incident = None
    try:
        incident = IncidentRepository(db).get_by_id(review.alert_id)
    except SQLAlchemyError as exc:  # banco indisponível: segue com o fallback em memória
        logger.warning(f"Banco indisponível na revisão HITL: {exc}")

    if incident is not None:
        alert_data = {"alarm_score": incident.alarm_score, "camera_id": incident.camera_id}
    else:
        alert_data = _alerts_store.get(review.alert_id)
    if not alert_data:
        raise HTTPException(status_code=404, detail="Alert não encontrado")

    # Cria decisão
    decision_data = {
        "decision_id": decision_id,
        "alert_id": review.alert_id,
        "operator_id": operator_id,
        "decision": review.decision,
        "justification": review.justification,
        "decided_at": datetime.now(),
        "alert_score": alert_data["alarm_score"],
        "alert_camera": alert_data["camera_id"],
    }

    _decisions_store[decision_id] = decision_data

    # Atualiza estatísticas do operador
    if operator_id not in _operator_stats:
        _operator_stats[operator_id] = {
            "operator_id": operator_id,
            "total_reviews": 0,
            "dismissals": 0,
            "escalations": 0,
            "decision_times": [],
        }

    stats = _operator_stats[operator_id]
    stats["total_reviews"] += 1
    if review.decision == "dismiss":
        stats["dismissals"] += 1
    elif review.decision == "escalate":
        stats["escalations"] += 1

    if incident is not None and review.decision in ("dismiss", "escalate"):
        IncidentRepository(db).update_status(
            incident_id=review.alert_id,
            status="dismissed" if review.decision == "dismiss" else "escalated",
            operator_id=operator_id,
            decision=review.decision,
            justification=review.justification,
        )

    # Atualiza alert (marca como revisado)
    alert_data["reviewed_at"] = datetime.now()
    alert_data["operator_id"] = operator_id
    alert_data["review_decision"] = review.decision

    if review.decision == "escalate":
        alert_data["status"] = "escalated"
        # TODO: Disparar notificação às autoridades
    elif review.decision == "dismiss":
        alert_data["status"] = "dismissed"

    return HitlDecision(**decision_data)


@router.get("/decisions/{alert_id}", response_model=list[HitlDecision])
async def get_alert_decisions(alert_id: str, operator: dict = Depends(get_current_operator)):
    """Retorna todas as decisões para um alerta (pode ter múltiplas)."""
    decisions = [d for d in _decisions_store.values() if d["alert_id"] == alert_id]
    return [HitlDecision(**d) for d in decisions]


@router.get("/operators/{operator_id}/stats", response_model=OperatorStats)
async def get_operator_stats(operator_id: str, operator: dict = Depends(get_current_operator)):
    """Retorna estatísticas de desempenho do operador."""
    if operator_id not in _operator_stats:
        return OperatorStats(
            operator_id=operator_id,
            total_reviews=0,
            dismissals=0,
            escalations=0,
            avg_decision_time_seconds=0.0,
            escalation_rate=0.0,
        )

    stats = _operator_stats[operator_id]
    total = stats["total_reviews"]

    return OperatorStats(
        operator_id=operator_id,
        total_reviews=total,
        dismissals=stats["dismissals"],
        escalations=stats["escalations"],
        avg_decision_time_seconds=0.0,  # TODO: Calcular
        escalation_rate=stats["escalations"] / total if total > 0 else 0.0,
    )


@router.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket):
    """
    WebSocket para fila de alertas pendentes de revisão.

    Dashboard conecta para receber alertas que precisam de revisão HITL.
    Requer ``?token=<JWT>``.
    """
    await websocket.accept()
    if await authenticate_websocket(websocket) is None:
        return

    from src.cloud.api.routes.alerts import _alerts_store

    try:
        while True:
            # Envia alertas pendentes
            pending = [a for a in _alerts_store.values() if a["status"] == "pending" and a["requires_hitl"]]

            if pending:
                await websocket.send_json(
                    {
                        "type": "queue_update",
                        "pending_count": len(pending),
                        "alerts": pending[:20],  # Top 20 mais recentes
                    }
                )

            # Aguarda 5 segundos antes de próximo update
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.debug("Cliente do WebSocket da fila HITL desconectou")


@router.get("/dashboard/summary")
async def get_dashboard_summary(operator: dict = Depends(get_current_operator)):
    """Retorna resumo do dashboard HITL."""
    from src.cloud.api.routes.alerts import _alerts_store

    now = datetime.now()

    pending = [a for a in _alerts_store.values() if a["status"] == "pending"]
    escalated = [a for a in _alerts_store.values() if a["status"] == "escalated"]
    dismissed = [a for a in _alerts_store.values() if a["status"] == "dismissed"]

    return {
        "pending_count": len(pending),
        "escalated_count": len(escalated),
        "dismissed_count": len(dismissed),
        "total_alerts": len(_alerts_store),
        "avg_score_pending": sum(a["alarm_score"] for a in pending) / len(pending) if pending else 0,
        "oldest_pending_minutes": (now - min(a["created_at"] for a in pending)).total_seconds() / 60 if pending else 0,
    }
