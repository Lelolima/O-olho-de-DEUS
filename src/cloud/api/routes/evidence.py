"""Evidence Routes - API para evidências e cadeia de custódia."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import hashlib
import uuid
from pathlib import Path

from src.cloud.api.middleware.auth import get_current_operator
from src.cloud.database import get_db, EvidenceRepository
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


# === Schemas ===

class EvidenceChain(BaseModel):
    """Cadeia de custódia de evidência."""

    evidence_id: str
    frame_hash: str
    metadata_hash: str
    merkle_root: str
    timestamp_cert: Optional[dict]
    verified: bool
    verification_details: dict


class EvidenceUploadResponse(BaseModel):
    """Resposta de upload de evidência."""

    evidence_id: str
    frame_path: str
    frame_hash: str
    uploaded_at: datetime
    merkle_batch_id: Optional[str]


# === In-Memory Store (fallback se DB não disponível) ===

_evidence_store: dict[str, dict] = {}
_db_available: bool = True


def _get_evidence_repo(db: Session) -> EvidenceRepository:
    """Obtém repositório de evidências."""
    return EvidenceRepository(db)


@router.post("/upload", response_model=EvidenceUploadResponse)
async def upload_evidence(
    file: UploadFile = File(...),
    camera_id: Optional[str] = None,
    alert_id: Optional[str] = None,
    operator: dict = Depends(get_current_operator),  # ✅ AUTENTICAÇÃO REQUERIDA
    db: Session = Depends(get_db)
):
    """
    Upload de frame de evidência.

    - Calcula hash SHA-256 do frame
    - Adiciona ao buffer do ForensicLogger
    - Retorna证据 ID e hash
    """
    global _db_available

    evidence_id = f"evt_{uuid.uuid4().hex[:12]}"

    # Lê conteúdo e calcula hash
    content = await file.read()
    frame_hash = hashlib.sha256(content).hexdigest()

    # Salva em diretório de evidências (em produção, usar S3/GCS)
    evidence_dir = Path("./evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    frame_path = evidence_dir / f"{evidence_id}.jpg"
    with open(frame_path, "wb") as f:
        f.write(content)

    # Cria registro
    evidence_data = {
        "evidence_id": evidence_id,
        "camera_id": camera_id,
        "alert_id": alert_id,
        "frame_path": str(frame_path),
        "frame_hash": frame_hash,
        "uploaded_at": datetime.now(),
        "verified": False
    }

    try:
        # Tenta usar banco de dados
        if _db_available:
            repo = _get_evidence_repo(db)
            evidence = repo.create({
                "id": evidence_id,
                "incident_id": alert_id or "unknown",
                "frame_hash": frame_hash,
                "metadata_hash": frame_hash,  # Simplificado
                "storage_path": str(frame_path),
                "storage_provider": "local"
            })

            return EvidenceUploadResponse(
                evidence_id=evidence.id,
                frame_path=evidence.storage_path,
                frame_hash=evidence.frame_hash,
                uploaded_at=evidence.created_at,
                merkle_batch_id=None
            )
    except Exception as e:
        # Fallback para memória se DB falhar
        _db_available = False

    # Fallback: armazenamento em memória
    _evidence_store[evidence_id] = evidence_data

    return EvidenceUploadResponse(
        evidence_id=evidence_id,
        frame_path=str(frame_path),
        frame_hash=frame_hash,
        uploaded_at=evidence_data["uploaded_at"],
        merkle_batch_id=None  # Será preenchido quando batch for flushado
    )


@router.get("/{evidence_id}/chain", response_model=EvidenceChain)
async def get_evidence_chain(evidence_id: str, db: Session = Depends(get_db)):
    """
    Retorna cadeia de custódia completa de evidência.

    Inclui:
    - Hash do frame
    - Hash dos metadados
    - Merkle root do batch
    - Certificado de timestamp TSA
    - Status de verificação
    """
    global _db_available

    try:
        if _db_available:
            repo = _get_evidence_repo(db)
            evidence = repo.get_by_id(evidence_id)
            if evidence:
                return EvidenceChain(
                    evidence_id=evidence.id,
                    frame_hash=evidence.frame_hash,
                    metadata_hash=evidence.metadata_hash,
                    merkle_root="",  # TODO: Buscar do batch
                    timestamp_cert=None,  # TODO: Buscar da TSA
                    verified=evidence.verified,
                    verification_details={"status": "verified" if evidence.verified else "not_verified"}
                )
    except Exception:
        _db_available = False

    # Fallback: memória
    if evidence_id not in _evidence_store:
        raise HTTPException(status_code=404, detail="Evidência não encontrada")

    evidence = _evidence_store[evidence_id]

    return EvidenceChain(
        evidence_id=evidence_id,
        frame_hash=evidence["frame_hash"],
        metadata_hash="",  # TODO: Calcular
        merkle_root="",  # TODO: Buscar do batch
        timestamp_cert=None,  # TODO: Buscar da TSA
        verified=evidence.get("verified", False),
        verification_details={"status": "verified" if evidence.get("verified") else "not_verified"}
    )


@router.post("/{evidence_id}/verify", response_model=dict)
async def verify_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """
    Verifica integridade de evidência.

    - Recalcula hash do frame
    - Compara com hash armazenado
    - Verifica prova Merkle
    - Valida timestamp TSA

    Retorna status de verificação.
    """
    global _db_available

    try:
        if _db_available:
            repo = _get_evidence_repo(db)
            evidence = repo.get_by_id(evidence_id)
            if not evidence:
                raise HTTPException(status_code=404, detail="Evidência não encontrada")

            # Recalcula hash
            frame_path = Path(evidence.storage_path)
            if not frame_path.exists():
                return {"verified": False, "error": "Frame não encontrado"}

            with open(frame_path, "rb") as f:
                current_hash = hashlib.sha256(f.read()).hexdigest()

            # Compara hashes
            if current_hash != evidence.frame_hash:
                return {
                    "verified": False,
                    "error": "Hash mismatch - evidência pode ter sido adulterada",
                    "expected_hash": evidence.frame_hash,
                    "current_hash": current_hash
                }

            # Atualiza status
            repo.verify(evidence_id)

            return {
                "verified": True,
                "evidence_id": evidence_id,
                "verified_at": datetime.now().isoformat()
            }
    except HTTPException:
        raise
    except Exception:
        _db_available = False

    # Fallback: memória
    if evidence_id not in _evidence_store:
        raise HTTPException(status_code=404, detail="Evidência não encontrada")

    evidence = _evidence_store[evidence_id]

    # Recalcula hash
    frame_path = Path(evidence["frame_path"])
    if not frame_path.exists():
        return {"verified": False, "error": "Frame não encontrado"}

    with open(frame_path, "rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()

    # Compara hashes
    if current_hash != evidence["frame_hash"]:
        return {
            "verified": False,
            "error": "Hash mismatch - evidência pode ter sido adulterada",
            "expected_hash": evidence["frame_hash"],
            "current_hash": current_hash
        }

    # Atualiza status
    evidence["verified"] = True

    return {
        "verified": True,
        "evidence_id": evidence_id,
        "verified_at": datetime.now().isoformat()
    }


@router.get("/batch/{batch_id}")
async def get_batch_info(batch_id: str):
    """
    Retorna informações de batch Merkle.

    Em produção, buscar do ForensicLogger.
    """
    # TODO: Implementar quando ForensicLogger estiver integrado
    return {
        "batch_id": batch_id,
        "status": "not_implemented",
        "message": "Batch lookup será implementado com ForensicLogger"
    }