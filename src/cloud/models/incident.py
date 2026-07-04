"""Incident Model - Modelo SQLAlchemy para incidentes/alertas."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, Text, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Incident(Base):
    """
    Modelo de Incidente para PostgreSQL.

    Armazena todos os alertas gerados pelo sistema,
    com links para evidências e decisões HITL.
    """

    __tablename__ = "incidents"

    # Primary key
    id = Column(String(36), primary_key=True)  # UUID

    # Dados do alerta
    camera_id = Column(String(50), nullable=False, index=True)
    alarm_score = Column(Float, nullable=False)
    behavior_indicators = Column(JSON, default=list)
    faces_count = Column(Integer, default=0)
    faces_data = Column(JSON, default=list)  # Embeddings, bounding boxes

    # Status
    status = Column(String(20), default="pending", index=True)
    # pending, reviewing, escalated, dismissed, resolved

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # HITL
    requires_hitl = Column(Boolean, default=True)
    operator_id = Column(String(50), nullable=True)
    review_decision = Column(String(20), nullable=True)  # dismiss, escalate
    review_justification = Column(Text, nullable=True)

    # Evidências
    frame_path = Column(String(500), nullable=True)
    frame_hash = Column(String(64), nullable=True)  # SHA-256
    metadata_hash = Column(String(64), nullable=True)
    merkle_root = Column(String(64), nullable=True)

    # Metadados extras
    metadata = Column(JSON, default=dict)

    # Índice composto para consultas frequenti
    __table_args__ = (
        Index("ix_incidents_status_created", "status", "created_at"),
        Index("ix_incidents_camera_created", "camera_id", "created_at"),
    )

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "alarm_score": self.alarm_score,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "requires_hitl": self.requires_hitl,
            "faces_count": self.faces_count,
            "operator_id": self.operator_id,
            "review_decision": self.review_decision
        }


class Evidence(Base):
    """
    Modelo de Evidência para PostgreSQL.

    Armazena metadados de frames/evidências,
    com hashes para cadeia de custódia.
    """

    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True)
    incident_id = Column(String(36), nullable=False, index=True)

    # Hashes para cadeia de custódia
    frame_hash = Column(String(64), nullable=False)
    metadata_hash = Column(String(64), nullable=False)

    # Armazenamento
    storage_path = Column(String(500), nullable=False)  # S3 key ou path local
    storage_provider = Column(String(20), default="local")  # local, s3, gcs

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Verificação
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "frame_hash": self.frame_hash,
            "storage_path": self.storage_path,
            "verified": self.verified,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class MerkleBatch(Base):
    """
    Modelo de Batch Merkle para PostgreSQL.

    Armazena roots de Merkle trees com certificados TSA.
    """

    __tablename__ = "merkle_batches"

    id = Column(String(50), primary_key=True)  # batch_YYYYMMDD_HHMMSS

    # Merkle root
    merkle_root = Column(String(64), nullable=False, unique=True, index=True)

    # Timestamp TSA
    tsa_status = Column(String(20), default="pending")  # pending, granted, rejected
    tsa_url = Column(String(200), nullable=True)
    tsa_cert_base64 = Column(Text, nullable=True)
    tsa_serial = Column(String(50), nullable=True)
    tsa_gen_time = Column(DateTime, nullable=True)

    # Contagem
    evidence_count = Column(Integer, nullable=False)
    evidence_hashes = Column(JSON, default=list)  # Lista de hashes no batch

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    flushed_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        """Converte para dict."""
        return {
            "id": self.id,
            "merkle_root": self.merkle_root,
            "tsa_status": self.tsa_status,
            "evidence_count": self.evidence_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "flushed_at": self.flushed_at.isoformat() if self.flushed_at else None
        }