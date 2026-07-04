"""
Database Configuration - Configuração de banco de dados PostgreSQL.

Este módulo gerencia a conexão com o banco de dados PostgreSQL,
criação de sessões e migrações.

Uso:
    from src.cloud.database import get_db, engine, Base

    # Criar tabelas
    Base.metadata.create_all(bind=engine)

    # Usar em rotas FastAPI
    @router.get("/")
    async def read_items(db: Session = Depends(get_db)):
        items = db.query(Item).all()
        return items
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from .models.incident import Incident, Evidence, MerkleBatch
from .models.hitl_decision import HitlDecision, OperatorSession

# URL do banco de dados de variável de ambiente
# Formato: postgresql://user:password@host:port/database
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/olho_de_deus"
)

# Modo de fallback para SQLite (desenvolvimento/testes)
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    DATABASE_URL = "sqlite:///./olho_de_deus.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=40,
        pool_pre_ping=True,  # Verifica conexões antes de usar
        pool_recycle=3600    # Recicla após 1 hora
    )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base para modelos
DatabaseBase = Incident.__class__.metadata


def create_tables():
    """Cria todas as tabelas no banco de dados."""
    DatabaseBase.create_all(bind=engine)
    print("✅ Tabelas criadas com sucesso")


def drop_tables():
    """Remove todas as tabelas (cuidado!)."""
    DatabaseBase.drop_all(bind=engine)
    print("⚠️ Tabelas removidas")


@contextmanager
def get_db_context():
    """
    Context manager para sessão de banco de dados.

    Uso:
        with get_db_context() as db:
            items = db.query(Incident).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_db():
    """
    Dependency para FastAPI.

    Uso:
        @router.get("/")
        async def read_items(db: Session = Depends(get_db)):
            return db.query(Incident).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === Repositórios ===

class IncidentRepository:
    """Repositório para operações com Incidentes."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, incident_data: dict) -> Incident:
        """Cria novo incidente."""
        incident = Incident(**incident_data)
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def get_by_id(self, incident_id: str) -> Incident | None:
        """Busca incidente por ID."""
        return self.db.query(Incident).filter(
            Incident.id == incident_id
        ).first()

    def list(
        self,
        status: str | None = None,
        camera_id: str | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Incident]:
        """Lista incidentes com filtros."""
        query = self.db.query(Incident)

        if status:
            query = query.filter(Incident.status == status)
        if camera_id:
            query = query.filter(Incident.camera_id == camera_id)

        return (
            query.order_by(Incident.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def update_status(
        self,
        incident_id: str,
        status: str,
        operator_id: str | None = None,
        decision: str | None = None,
        justification: str | None = None
    ) -> Incident | None:
        """Atualiza status de incidente."""
        incident = self.get_by_id(incident_id)
        if not incident:
            return None

        incident.status = status
        if operator_id:
            incident.operator_id = operator_id
        if decision:
            incident.review_decision = decision
        if justification:
            incident.review_justification = justification
        if status in ["escalated", "dismissed"]:
            incident.reviewed_at = None  # Will be set properly

        self.db.commit()
        self.db.refresh(incident)
        return incident

    def count_by_status(self) -> dict[str, int]:
        """Conta incidentes por status."""
        from sqlalchemy import func

        results = self.db.query(
            Incident.status,
            func.count(Incident.id)
        ).group_by(Incident.status).all()

        return {status: count for status, count in results}


class EvidenceRepository:
    """Repositório para operações com Evidências."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, evidence_data: dict) -> Evidence:
        """Cria nova evidência."""
        evidence = Evidence(**evidence_data)
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def get_by_id(self, evidence_id: str) -> Evidence | None:
        """Busca evidência por ID."""
        return self.db.query(Evidence).filter(
            Evidence.id == evidence_id
        ).first()

    def list_by_incident(self, incident_id: str) -> list[Evidence]:
        """Lista evidências de um incidente."""
        return self.db.query(Evidence).filter(
            Evidence.incident_id == incident_id
        ).all()

    def verify(self, evidence_id: str) -> Evidence | None:
        """Marca evidência como verificada."""
        evidence = self.get_by_id(evidence_id)
        if not evidence:
            return None

        evidence.verified = True
        evidence.verified_at = None  # Will be set properly
        self.db.commit()
        self.db.refresh(evidence)
        return evidence


class MerkleBatchRepository:
    """Repositório para operações com Batches Merkle."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, batch_data: dict) -> MerkleBatch:
        """Cria novo batch Merkle."""
        batch = MerkleBatch(**batch_data)
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def get_by_root(self, merkle_root: str) -> MerkleBatch | None:
        """Busca batch por Merkle root."""
        return self.db.query(MerkleBatch).filter(
            MerkleBatch.merkle_root == merkle_root
        ).first()

    def update_tsa_status(
        self,
        batch_id: str,
        tsa_status: str,
        tsa_url: str | None = None,
        tsa_cert_base64: str | None = None,
        tsa_serial: str | None = None,
        tsa_gen_time: str | None = None
    ) -> MerkleBatch | None:
        """Atualiza status do carimbo TSA."""
        batch = self.db.query(MerkleBatch).filter(
            MerkleBatch.id == batch_id
        ).first()

        if not batch:
            return None

        batch.tsa_status = tsa_status
        if tsa_url:
            batch.tsa_url = tsa_url
        if tsa_cert_base64:
            batch.tsa_cert_base64 = tsa_cert_base64
        if tsa_serial:
            batch.tsa_serial = tsa_serial
        if tsa_gen_time:
            batch.tsa_gen_time = None  # Will be set properly
        if tsa_status in ["granted", "rejected"]:
            batch.flushed_at = None  # Will be set properly

        self.db.commit()
        self.db.refresh(batch)
        return batch


class HitlDecisionRepository:
    """Repositório para operações com Decisões HITL."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, decision_data: dict) -> HitlDecision:
        """Cria nova decisão HITL."""
        decision = HitlDecision(**decision_data)
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def list_by_operator(
        self,
        operator_id: str,
        limit: int = 100
    ) -> list[HitlDecision]:
        """Lista decisões de um operador."""
        return (
            self.db.query(HitlDecision)
            .filter(HitlDecision.operator_id == operator_id)
            .order_by(HitlDecision.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_stats(self, operator_id: str) -> dict:
        """Retorna estatísticas de um operador."""
        from sqlalchemy import func

        total = self.db.query(func.count(HitlDecision.id)).filter(
            HitlDecision.operator_id == operator_id
        ).scalar()

        escalations = self.db.query(func.count(HitlDecision.id)).filter(
            HitlDecision.operator_id == operator_id,
            HitlDecision.decision == "escalate"
        ).scalar()

        dismissals = self.db.query(func.count(HitlDecision.id)).filter(
            HitlDecision.operator_id == operator_id,
            HitlDecision.decision == "dismiss"
        ).scalar()

        return {
            "total": total,
            "escalations": escalations,
            "dismissals": dismissals,
            "escalation_rate": escalations / total if total > 0 else 0
        }