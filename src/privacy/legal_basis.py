"""Legal Basis - Registro de base legal para processamento LGPD."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LegalBasis(str, Enum):
    """
    Bases legais para processamento de dados pessoais (LGPD Art. 7º).

    Para dados sensíveis (Art. 11º), bases adicionais se aplicam.
    """

    CONSENTIMENTO = "consentimento"  # Art. 7º, I
    OBRIGACAO_LEGAL = "obrigacao_legal"  # Art. 7º, II
    EXECUCAO_POLITICA_PUBLICA = "execucao_politica_publica"  # Art. 7º, III
    ESTUDOS_PESQUISA = "estudos_pesquisa"  # Art. 7º, IX
    EXECUCAO_CONTRATO = "execucao_contrato"  # Art. 7º, V
    EXERCICIO_DIREITO = "exercicio_direito"  # Art. 7º, VI
    PROTECAO_VIDA = "protecao_vida"  # Art. 7º, VII
    SEGURANCA_PUBLICA = "seguranca_publica"  # Art. 7º, VIII + Lei 13.848/2019
    LEGITIMO_INTERESSE = "legitimo_interesse"  # Art. 7º, IX

    # Bases específicas para dados sensíveis (Art. 11º)
    CONSENTIMENTO_SENSIVEL = "consentimento_sensivel"  # Art. 11º, I
    OBRIGACAO_LEGAL_SENSIVEL = "obrigacao_legal_sensivel"  # Art. 11º, II
    SAUDE = "saude"  # Art. 11º, II (profissional de saúde)


class DataCategory(str, Enum):
    """Categorias de dados pessoais processados."""

    IMAGEM_FACE = "imagem_face"
    EMBEDDING_FACIAL = "embedding_facial"
    COMPORTAMENTO = "comportamento"
    LOCALIZACAO = "localizacao"
    HORARIO = "horario"
    ATRIBUTOS_SENSIVEIS = "atributos_sensiveis"  # Raça, gênero, idade (se coletado)


@dataclass
class ProcessingRecord:
    """
    Registro de processamento de dados (LGPD Art. 37).

    Controlador deve manter registro de todas operações de processamento.
    """

    purpose: str  # Finalidade do processamento
    legal_basis: LegalBasis  # Base legal
    data_categories: list  # Categorias de dados processados
    retention_days: int  # Prazo de retenção
    data_controller: str = ""  # Controlador (empresa/órgão)
    operator_id: Optional[str] = None  # Operador que realizou
    consent_record_id: Optional[str] = None  # ID do consentimento (se aplicável)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    # Metadados adicionais
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calcula data de expiração automaticamente."""
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=self.retention_days)

    def is_expired(self) -> bool:
        """Verifica se registro expirou."""
        return datetime.now() > self.expires_at

    def days_until_expiration(self) -> int:
        """Retorna dias restantes até expiração."""
        delta = self.expires_at - datetime.now()
        return max(0, delta.days)

    def to_dict(self) -> dict:
        """Serializa para dict."""
        return {
            "purpose": self.purpose,
            "legal_basis": self.legal_basis.value,
            "data_categories": [c.value for c in self.data_categories],
            "retention_days": self.retention_days,
            "data_controller": self.data_controller,
            "operator_id": self.operator_id,
            "consent_record_id": self.consent_record_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "days_until_expiration": self.days_until_expiration(),
            "metadata": self.metadata
        }


class LegalBasisRegistry:
    """
    Registro centralizado de bases legais para processamento.

    Uso:
        registry = LegalBasisRegistry()

        # Register processing activity
        record = registry.register_processing(
            purpose="Segurança patrimonial",
            legal_basis=LegalBasis.SEGURANCA_PUBLICA,
            data_categories=[DataCategory.IMAGEM_FACE, DataCategory.COMPORTAMENTO],
            retention_days=90
        )

        # Check if processing is allowed
        if registry.is_processing_allowed(record):
            process_data()
    """

    def __init__(self, default_controller: str = ""):
        """
        Inicializa registro.

        Args:
            default_controller: Nome do controlador de dados
        """
        self.default_controller = default_controller
        self._records: Dict[str, ProcessingRecord] = {}

    def register_processing(
        self,
        purpose: str,
        legal_basis: LegalBasis,
        data_categories: list,
        retention_days: int,
        consent_record_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> ProcessingRecord:
        """
        Registra nova operação de processamento.

        Args:
            purpose: Finalidade do processamento
            legal_basis: Base legal LGPD
            data_categories: Categorias de dados processados
            retention_days: Dias de retenção
            consent_record_id: ID do termo de consentimento (se aplicável)
            operator_id: Operador responsável
            metadata: Metadados adicionais

        Returns:
            ProcessingRecord criado
        """
        import uuid

        record_id = f"proc_{uuid.uuid4().hex[:12]}"

        record = ProcessingRecord(
            purpose=purpose,
            legal_basis=legal_basis,
            data_categories=data_categories,
            retention_days=retention_days,
            data_controller=self.default_controller,
            operator_id=operator_id,
            consent_record_id=consent_record_id,
            metadata=metadata or {}
        )

        self._records[record_id] = record

        logger.info(
            f"Registro de processamento criado: {record_id} - "
            f"Purpose: {purpose}, Legal Basis: {legal_basis.value}"
        )

        return record

    def is_processing_allowed(self, record_id: str) -> bool:
        """
        Verifica se processamento é permitido (não expirado).

        Args:
            record_id: ID do registro

        Returns:
            True se permitido, False se expirado ou não encontrado
        """
        if record_id not in self._records:
            logger.warning(f"Registro não encontrado: {record_id}")
            return False

        record = self._records[record_id]

        if record.is_expired():
            logger.warning(
                f"Processamento expirado: {record_id} - "
                f"Expirou em {record.expires_at}"
            )
            return False

        return True

    def get_record(self, record_id: str) -> Optional[ProcessingRecord]:
        """Retorna registro por ID."""
        return self._records.get(record_id)

    def cleanup_expired(self) -> int:
        """
        Remove registros expirados.

        Returns:
            Número de registros removidos
        """
        expired_count = 0

        for record_id in list(self._records.keys()):
            if self._records[record_id].is_expired():
                del self._records[record_id]
                expired_count += 1
                logger.info(f"Registro expirado removido: {record_id}")

        return expired_count

    def get_all_records(self) -> Dict[str, ProcessingRecord]:
        """Retorna todos registros."""
        return self._records.copy()

    def get_consent_records(self) -> Dict[str, ProcessingRecord]:
        """Retorna apenas registros baseados em consentimento."""
        return {
            rid: rec for rid, rec in self._records.items()
            if rec.legal_basis in [LegalBasis.CONSENTIMENTO, LegalBasis.CONSENTIMENTO_SENSIVEL]
        }

    def generate_lgpd_report(self) -> dict:
        """
        Gera relatório para autoridade (ANPD).

        Returns:
            Relatório de todas operações de processamento
        """
        records_by_basis = {}
        for record in self._records.values():
            basis = record.legal_basis.value
            if basis not in records_by_basis:
                records_by_basis[basis] = []
            records_by_basis[basis].append(record.to_dict())

        return {
            "generated_at": datetime.now().isoformat(),
            "controller": self.default_controller,
            "total_records": len(self._records),
            "active_records": sum(1 for r in self._records.values() if not r.is_expired()),
            "expired_records": sum(1 for r in self._records.values() if r.is_expired()),
            "records_by_legal_basis": records_by_basis,
            "data_categories_processed": list(set(
                cat.value
                for rec in self._records.values()
                for cat in rec.data_categories
            ))
        }


# Registry global
legal_basis_registry = LegalBasisRegistry()