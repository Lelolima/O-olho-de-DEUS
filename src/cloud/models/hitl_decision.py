"""HITL Decision Model - Modelo SQLAlchemy para decisões de operadores."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, Float
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class HitlDecision(Base):
    """
    Modelo de Decisão HITL para PostgreSQL.

    Armazena todas as decisões de operadores humanos,
    criando audit trail completo para compliance.
    """

    __tablename__ = "hitl_decisions"

    id = Column(String(36), primary_key=True)  # UUID

    # Links
    alert_id = Column(String(36), ForeignKey("incidents.id"), nullable=False, index=True)
    operator_id = Column(String(50), nullable=False, index=True)

    # Decisão
    decision = Column(String(20), nullable=False)  # dismiss, escalate
    justification = Column(Text, nullable=True)
    confidence_override = Column(Float, nullable=True)  # Se operador sobrescreveu score

    # Performance
    decision_time_seconds = Column(Float, nullable=True)  # Tempo para decidir

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Índice para consultas
    __table_args__ = (
        Index("ix_hitl_operator_created", "operator_id", "created_at"),
        Index("ix_hitl_alert", "alert_id"),
    )

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "operator_id": self.operator_id,
            "decision": self.decision,
            "justification": self.justification,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class OperatorSession(Base):
    """
    Modelo de Sessão de Operador para PostgreSQL.

    Rastreia sessões ativas de operadores no dashboard HITL.
    """

    __tablename__ = "operator_sessions"

    id = Column(String(36), primary_key=True)
    operator_id = Column(String(50), nullable=False, index=True)

    # Session
    token = Column(String(500), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6
    user_agent = Column(String(500), nullable=True)

    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Estatísticas da sessão
    alerts_reviewed = Column(Integer, default=0)
    escalations = Column(Integer, default=0)
    dismissals = Column(Integer, default=0)

    def is_active(self) -> bool:
        """Verifica se sessão ainda está ativa."""
        from datetime import timedelta
        timeout = timedelta(hours=8)
        return (
            self.ended_at is None and
            datetime.utcnow() - self.last_activity < timeout
        )