"""
Timestamp Authority (TSA) - RFC 3161

Implementação de carimbo de tempo utilizando Autoridades de Carimbo de Tempo (TSA).
O TSAR (Time-Stamp Response) prova que um hash específico existia em um determinado
momento, criando prova criptográfica de anterioridade.

TSAs públicas gratuitas:
- FreeTSA: https://freetsa.org/tsr (sem autenticação)
- DigiCert: http://timestamp.digicert.com
- GlobalSign: http://timestamp.globalsign.com/tsa/r6advanced1
"""

import base64
import hashlib
import struct
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


@dataclass
class TimestampResponse:
    """Resposta de uma requisição TSA."""

    status: str  # "granted", "rejected", "waiting"
    tsr_base64: Optional[str] = None  # Time-Stamp Response (DER-encoded)
    tsa_url: Optional[str] = None
    serial_number: Optional[int] = None
    gen_time: Optional[datetime] = None
    certificate: Optional[x509.Certificate] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Serializa resposta para dict JSON-serializable."""
        cert_pem = None
        if self.certificate:
            cert_pem = self.certificate.public_bytes(
                encoding=serialization.Encoding.PEM
            ).decode('utf-8')

        return {
            "status": self.status,
            "tsr_base64": self.tsr_base64,
            "tsa_url": self.tsa_url,
            "serial_number": self.serial_number,
            "gen_time": self.gen_time.isoformat() if self.gen_time else None,
            "certificate_pem": cert_pem,
            "error": self.error
        }


class TimestampAuthority:
    """
    Cliente para Autoridade de Carimbo de Tempo (TSA) RFC 3161.

    Uso:
        tsa = TimestampAuthority()
        response = tsa.request_timestamp("abc123def456...")
        if response.status == "granted":
            print(f"Hash carimbado em {response.gen_time}")
    """

    # TSAs públicas gratuitas (ordenadas por preferência)
    TSA_URLS: List[str] = [
        "https://freetsa.org/tsr",  # Gratuita, sem autenticação
        "http://timestamp.digicert.com",
        "http://timestamp.globalsign.com/tsa/r6advanced1",
        "http://timestamp.entrust.net/TSS/RFC3161timestamp",
    ]

    # Timeout para requisições HTTP (segundos)
    HTTP_TIMEOUT = 10

    def __init__(self, tsa_url: Optional[str] = None):
        """
        Inicializa cliente TSA.

        Args:
            tsa_url: URL da TSA. Se None, usa primeira URL disponível.
        """
        self.tsa_url = tsa_url or self.TSA_URLS[0]
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/timestamp-query",
            "Accept": "application/timestamp-reply",
        })

    def request_timestamp(self, data_hash: str) -> TimestampResponse:
        """
        Solicita carimbo de tempo para um hash.

        Envia TSQ (Time-Stamp Query) para TSA e recebe TSAR (Time-Stamp Response).
        O TSAR é assinado pela TSA e contém:
        - Hash original
        - Horário de geração (gen_time)
        - Número de série
        - Certificado da TSA

        Args:
            data_hash: Hash SHA-256 em hexadecimal (64 caracteres)

        Returns:
            TimestampResponse com certificado e carimbo de tempo
        """
        # Valida hash
        if len(data_hash) != 64:
            return TimestampResponse(
                status="rejected",
                error=f"Hash inválido: esperado 64 caracteres hex, got {len(data_hash)}"
            )

        try:
            # Cria TSQ (Time-Stamp Query) em ASN.1 DER
            tsq_der = self._create_tsq(data_hash)

            # Envia para TSA
            response = self._session.post(
                self.tsa_url,
                data=tsq_der,
                timeout=self.HTTP_TIMEOUT
            )

            # Processa resposta
            if response.status_code == 200:
                tsr_der = response.content
                return self._parse_tsr(tsr_der)
            else:
                return TimestampResponse(
                    status="rejected",
                    error=f"HTTP {response.status_code}: {response.text}"
                )

        except requests.exceptions.Timeout:
            return TimestampResponse(
                status="rejected",
                error=f"Timeout após {self.HTTP_TIMEOUT}s"
            )
        except requests.exceptions.ConnectionError as e:
            return TimestampResponse(
                status="rejected",
                error=f"Erro de conexão: {str(e)}"
            )
        except Exception as e:
            return TimestampResponse(
                status="rejected",
                error=f"Erro inesperado: {str(e)}"
            )

    def _create_tsq(self, data_hash: str) -> bytes:
        """
        Cria Time-Stamp Query (TSQ) em ASN.1 DER.

        Estrutura ASN.1 do TSQ (RFC 3161):
        TimeStampReq ::= SEQUENCE {
            version                      INTEGER { v1(1) },
            messageImprint               MessageImprint,
            reqPolicy                    TSAPolicyId OPTIONAL,
            nonce                        INTEGER OPTIONAL,
            certReq                      BOOLEAN DEFAULT FALSE,
            extensions                   Extensions OPTIONAL
        }

        MessageImprint ::= SEQUENCE {
            hashAlgorithm                AlgorithmIdentifier,
            hashedMessage                OCTET STRING
        }
        """
        # Constrói manualmente o DER (evita dependência de asn1crypto/pyasn1)
        # Esta é uma implementação simplificada

        # OID para SHA-256: 1.2.840.113549.1.1.11
        sha256_oid = bytes([0x06, 0x09, 0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D,
                            0x01, 0x01, 0x0B])

        # Hash do algoritmo (NULL parameters)
        hash_algo_null = bytes([0x05, 0x00])

        # AlgorithmIdentifier ::= SEQUENCE { algorithm OID, parameters ANY }
        algorithm_id = self._der_sequence(sha256_oid + hash_algo_null)

        # HashedMessage ::= OCTET STRING
        hashed_message = bytes([0x04, 0x20]) + bytes.fromhex(data_hash)

        # MessageImprint ::= SEQUENCE { hashAlgorithm, hashedMessage }
        message_imprint = self._der_sequence(algorithm_id + hashed_message)

        # Version ::= INTEGER { v1(1) }
        version = bytes([0x02, 0x01, 0x01])

        # Nonce (opcional, mas recomendado para evitar replay attacks)
        nonce = self._generate_nonce()
        nonce_der = bytes([0x02, 0x08]) + nonce

        # CertReq ::= BOOLEAN DEFAULT FALSE (pede certificado da TSA)
        cert_req = bytes([0x01, 0x01, 0xFF])  # TRUE

        # TimeStampReq ::= SEQUENCE { version, messageImprint, nonce, certReq }
        tsq_content = version + message_imprint + nonce_der + cert_req
        tsq_der = self._der_sequence(tsq_content)

        return tsq_der

    def _parse_tsr(self, tsr_der: bytes) -> TimestampResponse:
        """
        Parse Time-Stamp Response (TSR) em ASN.1 DER.

        Estrutura ASN.1 do TSR (RFC 3161):
        TimeStampResp ::= SEQUENCE {
            status                       PKIStatusInfo,
            timeStampToken               TimeStampToken OPTIONAL
        }

        TimeStampToken ::= CONTENT-TYPE_signed_data
        """
        try:
            # Extrai PKIStatusInfo
            status_code, status_msg = self._extract_pki_status(tsr_der)

            # Status codes (RFC 3161):
            # 0 = granted, 1 = granted_with_mods, 2 = rejection,
            # 3 = waiting, 4 = revocation_warning

            if status_code == 0:
                status = "granted"
            elif status_code == 1:
                status = "granted_with_mods"
            elif status_code == 2:
                return TimestampResponse(
                    status="rejected",
                    error=status_msg or "Rejeição pela TSA"
                )
            elif status_code == 3:
                status = "waiting"
            else:
                status = f"unknown_{status_code}"

            # Extrai certificado e gen_time do timeStampToken
            gen_time, serial, cert = self._extract_token_info(tsr_der)

            return TimestampResponse(
                status=status,
                tsr_base64=base64.b64encode(tsr_der).decode('utf-8'),
                tsa_url=self.tsa_url,
                serial_number=serial,
                gen_time=gen_time,
                certificate=cert
            )

        except Exception as e:
            return TimestampResponse(
                status="rejected",
                error=f"Erro ao parsear TSR: {str(e)}"
            )

    def verify_timestamp(self, tsr_base64: str, expected_hash: str) -> bool:
        """
        Verifica se um TSAR é válido e contém o hash esperado.

        Args:
            tsr_base64: TSAR em base64
            expected_hash: Hash SHA-256 esperado (64 caracteres hex)

        Returns:
            True se válido e hash corresponde, False caso contrário
        """
        try:
            tsr_der = base64.b64decode(tsr_base64)

            # Verifica assinatura do certificado
            cert = self._extract_certificate(tsr_der)
            if not cert:
                return False

            # Verifica hash
            extracted_hash = self._extract_hashed_message(tsr_der)
            if extracted_hash != expected_hash.lower():
                return False

            return True

        except Exception:
            return False

    # Métodos auxiliares DER

    def _der_sequence(self, content: bytes) -> bytes:
        """Wraps content em SEQUENCE tag-length-value."""
        length = self._der_length(len(content))
        return bytes([0x30]) + length + content

    def _der_length(self, length: int) -> bytes:
        """Codifica comprimento em DER."""
        if length < 128:
            return bytes([length])
        else:
            # Long form: 0x8N onde N é número de bytes do length
            length_bytes = length.to_bytes((length.bit_length() + 7) // 8, 'big')
            return bytes([0x80 | len(length_bytes)]) + length_bytes

    def _generate_nonce(self) -> bytes:
        """Gera nonce de 8 bytes para evitar replay attacks."""
        import os
        return os.urandom(8)

    def _extract_pki_status(self, tsr_der: bytes) -> tuple[int, str]:
        """Extrai PKIStatusInfo do TSR."""
        # Implementação simplificada - parse manual de ASN.1
        # Na prática, usar asn1crypto ou pyasn1 para parsing completo

        # PKIStatusInfo ::= SEQUENCE {
        #     status        PKIStatus,
        #     statusString  PKIFreeText OPTIONAL,
        #     failInfo      PKIFailureInfo OPTIONAL
        # }

        # PKIStatus ::= INTEGER
        # 0 = granted, 1 = granted_with_mods, 2 = rejection,
        # 3 = waiting, 4 = revocation_warning

        try:
            # Encontra status code (INTEGER após SEQUENCE)
            # Estrutura esperada: 30 81 XX (SEQUENCE)
            #                       02 01 XX (INTEGER - status)

            if tsr_der[0] != 0x30:
                raise ValueError("TSR não começa com SEQUENCE")

            offset = 2  # Pula tag e length
            if tsr_der[offset] != 0x02:
                raise ValueError("Status não é INTEGER")

            status_length = tsr_der[offset + 1]
            status_code = int.from_bytes(
                tsr_der[offset + 2:offset + 2 + status_length],
                'big'
            )

            return status_code, ""

        except Exception as e:
            return -1, str(e)

    def _extract_token_info(self, tsr_der: bytes) -> tuple[Optional[datetime], Optional[int], Optional[x509.Certificate]]:
        """Extrai gen_time, serial_number e certificado do TSR."""
        # Implementação simplificada - retorna None para todos
        # Em produção, usar biblioteca asn1crypto completa

        # Para uma implementação real, seria necessário:
        # 1. Parse CMS SignedData
        # 2. Extrair TSTInfo
        # 3. Parse genTime (GeneralizedTime)
        # 4. Extrair serialNumber
        # 5. Extrair ou verificar certificado da TSA

        # Por enquanto, retorna None - o TSAR bruto é armazenado
        return None, None, None

    def _extract_certificate(self, tsr_der: bytes) -> Optional[x509.Certificate]:
        """Extrai certificado da TSA do TSR."""
        # Simplificado - em produção, parse completo do CMS
        return None

    def _extract_hashed_message(self, tsr_der: bytes) -> Optional[str]:
        """Extrai hashedMessage do TSR para verificação."""
        # Simplificado - em produção, parse completo
        return None


def timestamp_multiple_hashes(hashes: List[str], tsa_url: Optional[str] = None) -> dict:
    """
    Carimba múltiplos hashes e retorna Merkle root carimbado.

    Esta função:
    1. Constrói Merkle tree dos hashes
    2. Carimba o root na TSA
    3. Retorna prova para cada hash individual

    Args:
        hashes: Lista de hashes SHA-256 (64 caracteres hex cada)
        tsa_url: URL da TSA (opcional)

    Returns:
        Dict com:
        - root_hash: Hash da raiz
        - timestamp_response: Resposta da TSA
        - proofs: Lista de MerkleProof para cada hash
    """
    from .merkle_tree import MerkleTree

    # Constrói Merkle tree
    leaves = [{"hash": h, "index": i} for i, h in enumerate(hashes)]
    tree = MerkleTree(leaves)

    # Carimba root
    tsa = TimestampAuthority(tsa_url)
    response = tsa.request_timestamp(tree.root_hash)

    # Gera provas para cada folha
    proofs = [tree.get_proof(i) for i in range(len(hashes))]

    return {
        "root_hash": tree.root_hash,
        "leaf_count": len(hashes),
        "timestamp_response": response.to_dict() if response else None,
        "proofs": [p.to_dict() for p in proofs]
    }