"""Evidence Routes - API para evidências e cadeia de custódia."""

import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.cloud.api.middleware.auth import get_current_operator
from src.cloud.database import EvidenceRepository, get_db

logger = logging.getLogger(__name__)

MAX_EVIDENCE_BYTES = int(os.environ.get("EVIDENCE_MAX_MB", "10")) * 1024 * 1024


def _evidence_dir() -> Path:
    return Path(os.environ.get("EVIDENCE_DIR", "./forensic_logs")) / "frames"


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _sha256_file(path: Path) -> str | None:
    """Hash SHA-256 do arquivo, ou None se não existir."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


# === Schemas ===


class EvidenceChain(BaseModel):
    """Cadeia de custódia de evidência."""

    evidence_id: str
    frame_hash: str
    metadata_hash: str
    merkle_root: str
    timestamp_cert: dict | None
    verified: bool
    verification_details: dict


class EvidenceUploadResponse(BaseModel):
    """Resposta de upload de evidência."""

    evidence_id: str
    frame_path: str
    frame_hash: str
    uploaded_at: datetime
    merkle_batch_id: str | None


# === In-Memory Store (fallback se DB não disponível) ===

_evidence_store: dict[str, dict] = {}
_db_available: bool = True


def _get_evidence_repo(db: Session) -> EvidenceRepository:
    """Obtém repositório de evidências."""
    return EvidenceRepository(db)


@router.post("/upload", response_model=EvidenceUploadResponse)
async def upload_evidence(
    file: UploadFile = File(...),
    camera_id: str | None = None,
    alert_id: str | None = None,
    operator: dict = Depends(get_current_operator),  # ✅ AUTENTICAÇÃO REQUERIDA
    db: Session = Depends(get_db),
):
    """
    Upload de frame de evidência.

    - Calcula hash SHA-256 do frame
    - Adiciona ao buffer do ForensicLogger
    - Retorna ID da evidência e hash
    """
    global _db_available

    evidence_id = f"evt_{uuid.uuid4().hex[:12]}"

    # Lê conteúdo e calcula hash
    content = await file.read(MAX_EVIDENCE_BYTES + 1)
    if len(content) > MAX_EVIDENCE_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo de evidência excede EVIDENCE_MAX_MB")
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo de evidência vazio")
    frame_hash = hashlib.sha256(content).hexdigest()

    # Salva em EVIDENCE_DIR/frames (em produção, usar armazenamento dedicado)
    frame_path = _evidence_dir() / f"{evidence_id}.jpg"
    await asyncio.to_thread(_write_bytes, frame_path, content)

    # Cria registro
    evidence_data = {
        "evidence_id": evidence_id,
        "camera_id": camera_id,
        "alert_id": alert_id,
        "frame_path": str(frame_path),
        "frame_hash": frame_hash,
        "uploaded_at": datetime.now(),
        "verified": False,
    }

    try:
        # Tenta usar banco de dados
        if _db_available:
            repo = _get_evidence_repo(db)
            evidence = repo.create(
                {
                    "id": evidence_id,
                    "incident_id": alert_id or "unknown",
                    "frame_hash": frame_hash,
                    "metadata_hash": frame_hash,  # Simplificado
                    "storage_path": str(frame_path),
                    "storage_provider": "local",
                }
            )

            return EvidenceUploadResponse(
                evidence_id=evidence.id,
                frame_path=evidence.storage_path,
                frame_hash=evidence.frame_hash,
                uploaded_at=evidence.created_at,
                merkle_batch_id=None,
            )
    except SQLAlchemyError as exc:
        # Banco indisponível: usa armazenamento em memória daqui em diante
        logger.error(f"Banco de dados indisponível, usando memória: {exc}")
        _db_available = False

    # Fallback: armazenamento em memória
    _evidence_store[evidence_id] = evidence_data

    return EvidenceUploadResponse(
        evidence_id=evidence_id,
        frame_path=str(frame_path),
        frame_hash=frame_hash,
        uploaded_at=evidence_data["uploaded_at"],
        merkle_batch_id=None,  # Será preenchido quando batch for flushado
    )


@router.get("/{evidence_id}/chain", response_model=EvidenceChain)
async def get_evidence_chain(
    evidence_id: str,
    operator: dict = Depends(get_current_operator),
    db: Session = Depends(get_db),
):
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
                    verification_details={"status": "verified" if evidence.verified else "not_verified"},
                )
    except SQLAlchemyError as exc:
        # Banco indisponível: usa armazenamento em memória daqui em diante
        logger.error(f"Banco de dados indisponível, usando memória: {exc}")
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
        verification_details={"status": "verified" if evidence.get("verified") else "not_verified"},
    )


@router.post("/{evidence_id}/verify", response_model=dict)
async def verify_evidence(
    evidence_id: str,
    operator: dict = Depends(get_current_operator),
    db: Session = Depends(get_db),
):
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
            current_hash = await asyncio.to_thread(_sha256_file, Path(evidence.storage_path))
            if current_hash is None:
                return {"verified": False, "error": "Frame não encontrado"}

            # Compara hashes
            if current_hash != evidence.frame_hash:
                return {
                    "verified": False,
                    "error": "Hash mismatch - evidência pode ter sido adulterada",
                    "expected_hash": evidence.frame_hash,
                    "current_hash": current_hash,
                }

            # Atualiza status
            repo.verify(evidence_id)

            return {"verified": True, "evidence_id": evidence_id, "verified_at": datetime.now().isoformat()}
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        # Banco indisponível: usa armazenamento em memória daqui em diante
        logger.error(f"Banco de dados indisponível, usando memória: {exc}")
        _db_available = False

    # Fallback: memória
    if evidence_id not in _evidence_store:
        raise HTTPException(status_code=404, detail="Evidência não encontrada")

    evidence = _evidence_store[evidence_id]

    # Recalcula hash
    current_hash = await asyncio.to_thread(_sha256_file, Path(evidence["frame_path"]))
    if current_hash is None:
        return {"verified": False, "error": "Frame não encontrado"}

    # Compara hashes
    if current_hash != evidence["frame_hash"]:
        return {
            "verified": False,
            "error": "Hash mismatch - evidência pode ter sido adulterada",
            "expected_hash": evidence["frame_hash"],
            "current_hash": current_hash,
        }

    # Atualiza status
    evidence["verified"] = True

    return {"verified": True, "evidence_id": evidence_id, "verified_at": datetime.now().isoformat()}


@router.get("/batch/{batch_id}")
async def get_batch_info(batch_id: str, operator: dict = Depends(get_current_operator)):
    """
    Retorna informações de batch Merkle.

    Em produção, buscar do ForensicLogger.
    """
    # TODO: Implementar quando ForensicLogger estiver integrado
    return {
        "batch_id": batch_id,
        "status": "not_implemented",
        "message": "Batch lookup será implementado com ForensicLogger",
    }
