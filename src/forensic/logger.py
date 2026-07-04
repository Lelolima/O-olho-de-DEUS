"""
Forensic Logger - Logger forence com cadeia de custódia imutável.

Este módulo implementa logging de evidências com:
- Hash SHA-256 de cada evidência
- Agrupamento em batches com Merkle Tree
- Carimbo de tempo RFC 3161 (Timestamp Authority)
- Armazenamento à prova de violação

Uso:
    logger = ForensicLogger(log_dir="./forensic_logs")

    # Log evidência individual
    evidence = {
        "id": "evt_abc123",
        "camera_id": "CAM-001",
        "timestamp": "2026-07-03T14:32:18Z",
        "alarm_score": 0.97
    }
    logged = logger.log_evidence(evidence)

    # Fechar batch manualmente (se necessário)
    logger.flush_batch()
"""

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .merkle_tree import MerkleTree, MerkleProof
from .timestamp import TimestampAuthority, TimestampResponse


class ForensicLogger:
    """
    Logger forence com cadeia de custódia imutável.

    Características:
    - Hash SHA-256 de cada evidência (canonically sorted JSON)
    - Batch processing: acumula até N evidências antes de carimbar
    - Merkle Tree: root hash carimbado por TSA
    - Armazenamento redundante: evidence individual + batch record
    """

    # Tamanho padrão do batch antes de_flush
    DEFAULT_BATCH_SIZE = 100

    # Formato de arquivo
    EVIDENCE_FILENAME_FORMAT = "{date}/{evidence_id}.json"
    BATCH_FILENAME_FORMAT = "batch_{batch_id}.json"

    def __init__(
        self,
        log_dir: str,
        tsa_enabled: bool = True,
        tsa_url: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        archive_dir: Optional[str] = None
    ):
        """
        Inicializa Forensic Logger.

        Args:
            log_dir: Diretório base para logs
            tsa_enabled: Habilita carimbo de tempo TSA
            tsa_url: URL da TSA (default: usa primeira disponível)
            batch_size: Número de evidências por batch
            archive_dir: Diretório para archive de batches (default: log_dir/archives)
        """
        self.log_dir = Path(log_dir)
        self.tsa_enabled = tsa_enabled
        self.batch_size = batch_size
        self.archive_dir = Path(archive_dir) if archive_dir else self.log_dir / "archives"

        # Cria diretórios
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Buffer de evidências pendentes
        self.pending_evidence: List[dict] = []
        self.pending_hashes: List[str] = []

        # TSA client
        self.tsa = TimestampAuthority(tsa_url) if tsa_enabled else None

        # Contadores
        self.total_evidence_logged = 0
        self.total_batches_flushed = 0

    def log_evidence(self, evidence: dict) -> dict:
        """
        Registra evidência com hash forence.

        Args:
            evidence: Dict com dados da evidência. Deve conter:
                - id: Identificador único (ex: "evt_abc123")
                - timestamp: Timestamp ISO 8601
                - camera_id: Identificador da câmera
                - alarm_score: Score de alarme (0-1)
                - frame_path: (opcional) Path para frame da evidência
                - faces: (opcional) Lista de faces detectadas

        Returns:
            Evidence enriquecida com:
                - metadata_hash: Hash SHA-256 dos metadados
                - frame_sha256: (se frame_path existir) Hash do frame
                - logged_at: Timestamp de log
                - batch_pending: True se ainda não flushado
        """
        # Garante timestamp
        if "timestamp" not in evidence:
            evidence["timestamp"] = datetime.now().isoformat()

        # Hash do frame (se existir)
        if "frame_path" in evidence and evidence["frame_path"]:
            evidence["frame_sha256"] = self._hash_file(evidence["frame_path"])

        # Hash dos metadados (canonical JSON)
        evidence["metadata_hash"] = self._hash_metadata(evidence)

        # Adiciona ao buffer
        self.pending_evidence.append(evidence)
        self.pending_hashes.append(evidence["metadata_hash"])

        # Salva evidência individual (para recuperação rápida)
        self._save_individual_evidence(evidence)

        # Auto-flush se batch completo
        if len(self.pending_evidence) >= self.batch_size:
            batch_record = self.flush_batch()
            evidence["batch_record"] = batch_record
        else:
            evidence["batch_pending"] = True

        evidence["logged_at"] = datetime.now().isoformat()
        self.total_evidence_logged += 1

        return evidence

    def flush_batch(self) -> Optional[dict]:
        """
        Fecha Merkle tree do batch atual e carimba root na TSA.

        Returns:
            Batch record com merkle_root, timestamp_cert, etc.
            None se batch vazio
        """
        if not self.pending_evidence:
            return None

        batch_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Constrói Merkle tree
        leaves = [
            {
                "evidence_id": e["id"],
                "metadata_hash": e["metadata_hash"],
                "timestamp": e["timestamp"]
            }
            for e in self.pending_evidence
        ]
        tree = MerkleTree(leaves)

        # Carimba root na TSA
        timestamp_cert = None
        if self.tsa_enabled and self.tsa:
            response = self.tsa.request_timestamp(tree.root_hash)
            if response and response.status == "granted":
                timestamp_cert = response.to_dict()

        # Cria batch record
        batch_record = {
            "batch_id": batch_id,
            "merkle_root": tree.root_hash,
            "timestamp_cert": timestamp_cert,
            "evidence_count": len(self.pending_evidence),
            "evidence_ids": [e["id"] for e in self.pending_evidence],
            "evidence_hashes": [e["metadata_hash"] for e in self.pending_evidence],
            "leaf_proofs": [
                tree.get_proof(i).to_dict()
                for i in range(len(self.pending_evidence))
            ],
            "flushed_at": datetime.now().isoformat()
        }

        # Salva batch record
        self._save_batch_record(batch_record)

        # Limpa buffer
        self.pending_evidence = []
        self.pending_hashes = []
        self.total_batches_flushed += 1

        return batch_record

    def verify_evidence_chain(
        self,
        evidence_id: str,
        batch_record: dict
    ) -> dict:
        """
        Verifica cadeia de custódia de uma evidência.

        Args:
            evidence_id: ID da evidência
            batch_record: Batch record contendo a evidência

        Returns:
            Dict com:
                - valid: True se cadeia válida
                - merkle_proof_valid: True se prova Merkle válida
                - timestamp_valid: True se timestamp TSA válido
                - evidence_found: True se evidência encontrada no batch
                - details: Detalhes da verificação
        """
        result = {
            "evidence_id": evidence_id,
            "valid": True,
            "merkle_proof_valid": True,
            "timestamp_valid": True,
            "evidence_found": False,
            "details": {}
        }

        # Encontra evidência no batch
        try:
            index = batch_record["evidence_ids"].index(evidence_id)
            result["evidence_found"] = True
        except ValueError:
            result["valid"] = False
            result["details"]["error"] = "Evidência não encontrada no batch"
            return result

        # Recupera prova Merkle
        proof_data = batch_record["leaf_proofs"][index]
        expected_hash = batch_record["evidence_hashes"][index]

        # Verifica prova Merkle
        from .merkle_tree import MerkleProof
        proof = MerkleProof.from_dict(proof_data)

        from .merkle_tree import MerkleTree as MT
        # Cria árvore dummy para verificação
        is_valid = MT([]).verify_proof(proof)  # type: ignore

        if not is_valid:
            result["merkle_proof_valid"] = False
            result["valid"] = False
            result["details"]["error"] = "Prova Merkle inválida"

        # Verifica timestamp TSA (se existir)
        if batch_record.get("timestamp_cert"):
            ts_cert = batch_record["timestamp_cert"]
            if ts_cert.get("tsr_base64"):
                # Verificação simplificada
                if self.tsa:
                    ts_valid = self.tsa.verify_timestamp(
                        ts_cert["tsr_base64"],
                        batch_record["merkle_root"]
                    )
                    result["timestamp_valid"] = ts_valid
                    if not ts_valid:
                        result["valid"] = False
                        result["details"]["error"] = "Timestamp TSA inválido"

        result["details"]["merkle_root"] = batch_record["merkle_root"]
        result["details"]["leaf_index"] = index
        result["details"]["expected_hash"] = expected_hash

        return result

    def get_statistics(self) -> dict:
        """Retorna estatísticas do logger."""
        return {
            "total_evidence_logged": self.total_evidence_logged,
            "total_batches_flushed": self.total_batches_flushed,
            "pending_evidence_count": len(self.pending_evidence),
            "batch_size": self.batch_size,
            "tsa_enabled": self.tsa_enabled,
            "log_dir": str(self.log_dir),
            "archive_dir": str(self.archive_dir)
        }

    def _hash_file(self, file_path: str) -> str:
        """Calcula hash SHA-256 de arquivo."""
        sha256 = hashlib.sha256()
        path = Path(file_path)

        if not path.exists():
            return "file_not_found"

        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _hash_metadata(self, evidence: dict) -> str:
        """
        Calcula hash SHA-256 de metadados (canonical JSON).

        Remove campos voláteis (batch_pending, logged_at) antes de hash.
        """
        # Cria cópia sem campos voláteis
        evidence_copy = {
            k: v for k, v in evidence.items()
            if k not in ["batch_pending", "logged_at", "batch_record"]
        }

        # Canonicaliza JSON (sorted keys, no whitespace)
        canonical = json.dumps(
            evidence_copy,
            sort_keys=True,
            separators=(",", ":")
        )

        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _save_individual_evidence(self, evidence: dict):
        """Salva evidência individualmente para recuperação rápida."""
        date_str = evidence.get("timestamp", datetime.now().isoformat())[:10]
        date_dir = self.log_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{evidence['id']}.json"
        filepath = date_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)

    def _save_batch_record(self, batch_record: dict):
        """Salva batch record no archive."""
        filename = self.BATCH_FILENAME_FORMAT.format(
            batch_id=batch_record["batch_id"]
        )
        filepath = self.archive_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(batch_record, f, indent=2, ensure_ascii=False)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush automático."""
        if self.pending_evidence:
            self.flush_batch()


class HitlDecisionLogger:
    """
    Logger especializado em decisões HITL (Human-in-the-Loop).

    Registra todas as decisões de operadores do dashboard,
    criando audit trail para compliance e análise de viés.
    """

    def __init__(self, forensic_logger: ForensicLogger):
        """
        Inicializa HITL Decision Logger.

        Args:
            forensic_logger: ForensicLogger para registrar decisões
        """
        self.forensic_logger = forensic_logger

    def log_decision(
        self,
        alert_id: str,
        operator_id: str,
        decision: str,
        justification: Optional[str] = None
    ) -> dict:
        """
        Registra decisão de operador HITL.

        Args:
            alert_id: ID do alerta revisado
            operator_id: ID do operador
            decision: "dismiss" ou "escalate"
            justification: Justificativa opcional do operador

        Returns:
            Dict com decisão logada
        """
        evidence = {
            "id": f"hitl_{alert_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "hitl_decision",
            "alert_id": alert_id,
            "operator_id": operator_id,
            "decision": decision,
            "justification": justification,
            "timestamp": datetime.now().isoformat()
        }

        return self.forensic_logger.log_evidence(evidence)