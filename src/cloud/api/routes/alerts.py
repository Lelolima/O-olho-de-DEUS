"""Alert Routes - API para gerenciamento de alertas."""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi import Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from src.cloud.api.middleware.auth import get_current_operator
from src.cloud.database import get_db, IncidentRepository
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


# === Schemas ===

class AlertCreate(BaseModel):
    """Schema para criação de alerta."""

    camera_id: str
    alarm_score: float = Field(ge=0, le=1)
    behavior_indicators: List[str]
    frame_blurhash: Optional[str] = None
    faces_count: int = 0
    metadata: Optional[dict] = None


class AlertResponse(BaseModel):
    """Schema de resposta de alerta."""

    alert_id: str
    camera_id: str
    alarm_score: float
    status: str  # "pending", "reviewing", "escalated", "dismissed"
    created_at: datetime
    requires_hitl: bool
    faces_count: int


class AlertReview(BaseModel):
    """Schema para revisão HITL."""

    decision: str  # "dismiss" | "escalate"
    justification: Optional[str] = Field(None, max_length=500)
    operator_id: Optional[str] = None


# === In-Memory Store (fallback se DB não disponível) ===

_alerts_store: dict[str, dict] = {}
_db_available: bool = True


def _get_incident_repo(db: Session) -> IncidentRepository:
    """Obtém repositório de incidentes."""
    return IncidentRepository(db)


@router.post("/", response_model=AlertResponse, status_code=201)
async def create_alert(
    alert: AlertCreate,
    operator: dict = Depends(get_current_operator),
    db: Session = Depends(get_db)
):
    """
    Cria novo alerta de comportamento suspeito.

    - **camera_id**: Identificador da câmera
    - **alarm_score**: Score de alarme (0-1)
    - **behavior_indicators**: Lista de indicadores comportamentais
    - **faces_count**: Número de faces detectadas
    - **operator**: Operador autenticado (via JWT)
    """
    global _db_available

    alert_id = f"alert_{uuid.uuid4().hex[:12]}"

    # Determina status baseado no score
    if alert.alarm_score >= 0.95:
        status = "escalated"  # Crítico: notifica imediatamente
        requires_hitl = False
    elif alert.alarm_score >= 0.70:
        status = "pending"  # Requer revisão HITL
        requires_hitl = True
    else:
        status = "dismissed"  # Baixa confiança: apenas log
        requires_hitl = False

    try:
        # Tenta usar banco de dados
        if _db_available:
            repo = _get_incident_repo(db)
            incident_data = {
                "id": alert_id,
                "camera_id": alert.camera_id,
                "alarm_score": alert.alarm_score,
                "status": status,
                "requires_hitl": requires_hitl,
                "faces_count": alert.faces_count,
                "behavior_indicators": alert.behavior_indicators,
                "faces_data": [],
                "metadata": alert.metadata or {},
                "operator_id": operator["username"],
                "review_decision": None
            }
            incident = repo.create(incident_data)

            # Se crítico, dispara notificação imediata
            if status == "escalated":
                await _notify_authorities_immediate(incident_data)

            return AlertResponse(
                alert_id=incident.id,
                camera_id=incident.camera_id,
                alarm_score=incident.alarm_score,
                status=incident.status,
                created_at=incident.created_at,
                requires_hitl=incident.requires_hitl,
                faces_count=incident.faces_count
            )
    except Exception as e:
        # Fallback para memória se DB falhar
        _db_available = False

    # Fallback: armazenamento em memória
    alert_data = {
        "alert_id": alert_id,
        "camera_id": alert.camera_id,
        "alarm_score": alert.alarm_score,
        "status": status,
        "requires_hitl": requires_hitl,
        "faces_count": alert.faces_count,
        "behavior_indicators": alert.behavior_indicators,
        "frame_blurhash": alert.frame_blurhash,
        "metadata": alert.metadata or {},
        "created_at": datetime.now(),
        "reviewed_at": None,
        "operator_id": operator["username"],
        "review_decision": None
    }

    _alerts_store[alert_id] = alert_data

    # Se crítico, dispara notificação imediata
    if status == "escalated":
        await _notify_authorities_immediate(alert_data)

    return AlertResponse(**alert_data)


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    status: Optional[str] = None,
    camera_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Lista alertas com filtros opcionais."""
    global _db_available

    try:
        if _db_available:
            repo = _get_incident_repo(db)
            incidents = repo.list(
                status=status,
                camera_id=camera_id,
                limit=limit,
                offset=offset
            )
            return [
                AlertResponse(
                    alert_id=inc.id,
                    camera_id=inc.camera_id,
                    alarm_score=inc.alarm_score,
                    status=inc.status,
                    created_at=inc.created_at,
                    requires_hitl=inc.requires_hitl,
                    faces_count=inc.faces_count
                )
                for inc in incidents
            ]
    except Exception:
        _db_available = False

    # Fallback: memória
    results = []
    for alert_data in _alerts_store.values():
        if status and alert_data["status"] != status:
            continue
        if camera_id and alert_data["camera_id"] != camera_id:
            continue
        results.append(alert_data)

    results.sort(key=lambda x: x["created_at"], reverse=True)
    return [AlertResponse(**r) for r in results[offset:offset + limit]]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Obtém detalhes de um alerta específico."""
    global _db_available

    try:
        if _db_available:
            repo = _get_incident_repo(db)
            incident = repo.get_by_id(alert_id)
            if incident:
                return AlertResponse(
                    alert_id=incident.id,
                    camera_id=incident.camera_id,
                    alarm_score=incident.alarm_score,
                    status=incident.status,
                    created_at=incident.created_at,
                    requires_hitl=incident.requires_hitl,
                    faces_count=incident.faces_count
                )
    except Exception:
        _db_available = False

    # Fallback: memória
    if alert_id not in _alerts_store:
        raise HTTPException(status_code=404, detail="Alert não encontrado")

    return AlertResponse(**_alerts_store[alert_id])


@router.post("/{alert_id}/review", response_model=AlertResponse)
async def review_alert(
    alert_id: str,
    review: AlertReview,
    operator: dict = Depends(get_current_operator),
    db: Session = Depends(get_db)
):
    """
    Operador HITL submete revisão de alerta.

    - **decision**: "dismiss" ou "escalate"
    - **justification**: Justificativa opcional
    - **operator_id**: ID do operador (se autenticado)
    """
    global _db_available

    try:
        if _db_available:
            repo = _get_incident_repo(db)
            incident = repo.get_by_id(alert_id)

            if not incident:
                raise HTTPException(status_code=404, detail="Alert não encontrado")

            if incident.status != "pending":
                raise HTTPException(
                    status_code=400,
                    detail=f"Alert já está {incident.status}, não pode ser revisado"
                )

            # Atualiza status baseado na decisão
            new_status = "dismissed" if review.decision == "dismiss" else "escalated"

            updated = repo.update_status(
                incident_id=alert_id,
                status=new_status,
                operator_id=operator["username"],
                decision=review.decision,
                justification=review.justification
            )

            # Dispara notificação às autoridades se escalado
            if review.decision == "escalate":
                await _notify_authorities({
                    "alert_id": alert_id,
                    "alarm_score": updated.alarm_score
                })

            return AlertResponse(
                alert_id=updated.id,
                camera_id=updated.camera_id,
                alarm_score=updated.alarm_score,
                status=updated.status,
                created_at=updated.created_at,
                requires_hitl=updated.requires_hitl,
                faces_count=updated.faces_count
            )
    except HTTPException:
        raise
    except Exception as e:
        _db_available = False

    # Fallback: memória
    if alert_id not in _alerts_store:
        raise HTTPException(status_code=404, detail="Alert não encontrado")

    alert_data = _alerts_store[alert_id]

    if alert_data["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Alert já está {alert_data['status']}, não pode ser revisado"
        )

    # Atualiza status baseado na decisão
    if review.decision == "dismiss":
        alert_data["status"] = "dismissed"
    elif review.decision == "escalate":
        alert_data["status"] = "escalated"
        # Dispara notificação às autoridades
        await _notify_authorities(alert_data)

    # Metadados da revisão
    alert_data["reviewed_at"] = datetime.now()
    alert_data["operator_id"] = review.operator_id or operator["username"]
    alert_data["review_decision"] = review.decision
    alert_data["review_justification"] = review.justification

    return AlertResponse(**alert_data)


@router.websocket("/ws/live")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket para push de alertas em tempo real.

    Dashboard HITL conecta neste endpoint para receber
    alertas assim que são criados.
    """
    await websocket.accept()

    # Envia alertas pendentes existentes
    pending = [
        a for a in _alerts_store.values()
        if a["status"] == "pending"
    ]
    for alert in pending[:10]:  # Limita a 10 mais recentes
        await websocket.send_json({"type": "existing", "alert": alert})

    # Nota: Em produção, usar pub/sub para notificações em tempo real
    try:
        while True:
            # Mantém conexão viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass


# === Helpers ===

async def _notify_authorities(alert_data: dict):
    """Notifica autoridades (polícia, segurança)."""
    # Em produção: integrar com sistema de despacho (911, 190)
    # Ou enviar webhook para API da secretaria de segurança
    pass


async def _notify_authorities_immediate(alert_data: dict):
    """Notificação imediata para alertas críticos."""
    # Críticos (>95%) notificam sem esperar HITL
    pass