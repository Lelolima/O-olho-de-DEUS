"""HITL Routes - API para revisão humana de alertas."""

from fastapi import APIRouter, HTTPException, Depends, WebSocket
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])


# === Schemas ===

class HitlReviewRequest(BaseModel):
    """Solicitação de revisão HITL."""

    alert_id: str
    decision: str  # "dismiss" | "escalate" | "request_more_info"
    justification: Optional[str] = Field(None, max_length=500)
    confidence_override: Optional[float] = Field(None, ge=0, le=1)


class HitlDecision(BaseModel):
    """Decisão HITL registrada."""

    decision_id: str
    alert_id: str
    operator_id: str
    decision: str
    justification: Optional[str]
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
async def submit_hitl_review(review: HitlReviewRequest, operator_id: Optional[str] = "anonymous"):
    """
    Operador submete decisão de revisão HITL.

    Esta decisão é registrada no log forense para audit trail.
    """
    import uuid

    decision_id = f"hitl_{uuid.uuid4().hex[:12]}"

    # Recupera dados do alerta (em produção, buscar do PostgreSQL)
    from src.cloud.api.routes.alerts import _alerts_store

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
        "alert_camera": alert_data["camera_id"]
    }

    _decisions_store[decision_id] = decision_data

    # Atualiza estatísticas do operador
    if operator_id not in _operator_stats:
        _operator_stats[operator_id] = {
            "operator_id": operator_id,
            "total_reviews": 0,
            "dismissals": 0,
            "escalations": 0,
            "decision_times": []
        }

    stats = _operator_stats[operator_id]
    stats["total_reviews"] += 1
    if review.decision == "dismiss":
        stats["dismissals"] += 1
    elif review.decision == "escalate":
        stats["escalations"] += 1

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


@router.get("/decisions/{alert_id}", response_model=List[HitlDecision])
async def get_alert_decisions(alert_id: str):
    """Retorna todas as decisões para um alerta (pode ter múltiplas)."""
    decisions = [
        d for d in _decisions_store.values()
        if d["alert_id"] == alert_id
    ]
    return [HitlDecision(**d) for d in decisions]


@router.get("/operators/{operator_id}/stats", response_model=OperatorStats)
async def get_operator_stats(operator_id: str):
    """Retorna estatísticas de desempenho do operador."""
    if operator_id not in _operator_stats:
        return OperatorStats(
            operator_id=operator_id,
            total_reviews=0,
            dismissals=0,
            escalations=0,
            avg_decision_time_seconds=0.0,
            escalation_rate=0.0
        )

    stats = _operator_stats[operator_id]
    total = stats["total_reviews"]

    return OperatorStats(
        operator_id=operator_id,
        total_reviews=total,
        dismissals=stats["dismissals"],
        escalations=stats["escalations"],
        avg_decision_time_seconds=0.0,  # TODO: Calcular
        escalation_rate=stats["escalations"] / total if total > 0 else 0.0
    )


@router.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket):
    """
    WebSocket para fila de alertas pendentes de revisão.

    Dashboard conecta para receber alertas que precisam de revisão HITL.
    """
    await websocket.accept()

    from src.cloud.api.routes.alerts import _alerts_store

    try:
        while True:
            # Envia alertas pendentes
            pending = [
                a for a in _alerts_store.values()
                if a["status"] == "pending" and a["requires_hitl"]
            ]

            if pending:
                await websocket.send_json({
                    "type": "queue_update",
                    "pending_count": len(pending),
                    "alerts": pending[:20]  # Top 20 mais recentes
                })

            # Aguarda 5 segundos antes de próximo update
            await websocket.receive_text()

    except Exception:
        pass


@router.get("/dashboard/summary")
async def get_dashboard_summary():
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
        "oldest_pending_minutes": (now - min(a["created_at"] for a in pending)).total_seconds() / 60 if pending else 0
    }