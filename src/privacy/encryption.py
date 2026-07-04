"""
Encryption Manager - Criptografia de evidências com rotaçãode chaves.

Implementa envelope encryption com Fernet (AES-128-CBC + HMAC-SHA256),
rotação automática de chaves e integração opcional com cofres de secretos.
"""

import base64
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class EncryptedData:
    """Dados criptografados com metadados de chave."""

    ciphertext: bytes
    key_id: str
    nonce: bytes = field(default_factory=lambda: os.urandom(16))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Serializa para dict JSON-serializable."""
        return {
            "ciphertext_b64": base64.b64encode(self.ciphertext).decode(),
            "key_id": self.key_id,
            "nonce_b64": base64.b64encode(self.nonce).decode(),
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'EncryptedData':
        """Deserializa de dict."""
        return cls(
            ciphertext=base64.b64decode(data["ciphertext_b64"]),
            key_id=data["key_id"],
            nonce=base64.b64decode(data["nonce_b64"]),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class KeyMetadata:
    """Metadados de uma chave de criptografia."""

    key_id: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    usage_count: int = 0
    max_usages: int = 10000

    def should_rotate(self) -> bool:
        """Verifica se chave deve ser rotacionada."""
        # Verifica por tempo
        if self.expires_at and datetime.now() > self.expires_at:
            return True
        # Verifica por uso
        if self.usage_count >= self.max_usages:
            return True
        return False

    def to_dict(self) -> dict:
        """Serializa para dict."""
        return {
            "key_id": self.key_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "max_usages": self.max_usages
        }


class EncryptionManager:
    """
    Gerenciador de criptografia com rotação de chaves.

    Usa Fernet para criptografia simétrica (AES-128-CBC + HMAC-SHA256).
    Suporta múltiplas chaves ativas para decrypt de dados antigos.

    Uso:
        mgr = EncryptionManager(master_key=b"32-bytes-key-here...")
        encrypted = mgr.encrypt(b"sensitive data")
        decrypted = mgr.decrypt(encrypted)
    """

    def __init__(
        self,
        master_key: Optional[bytes] = None,
        key_rotation_days: int = 30,
        max_usages_per_key: int = 10000,
        keys_dir: Optional[str] = None
    ):
        """
        Inicializa EncryptionManager.

        Args:
            master_key: Chave mestra (32 bytes). Se None, gera nova.
            key_rotation_days: Dias até rotação automática
            max_usages_per_key: Máximo de usos antes de rotação
            keys_dir: Diretório para armazenar chaves (opcional)
        """
        self.key_rotation_days = key_rotation_days
        self.max_usages_per_key = max_usages_per_key
        self.keys_dir = Path(keys_dir) if keys_dir else None

        # Chaves ativas (key_id -> Fernet)
        self._keys: Dict[str, Fernet] = {}
        self._key_metadata: Dict[str, KeyMetadata] = {}

        # Chave ativa atual
        self._active_key_id: Optional[str] = None

        # Inicializa ou carrega chave mestra
        if master_key:
            self._master_key = master_key
        else:
            self._master_key = self._generate_master_key()
            self._save_master_key()

        # Carrega chaves existentes ou cria primeira
        if self.keys_dir and self.keys_dir.exists():
            self._load_keys()
        else:
            self._create_new_key()

    def encrypt(self, data: bytes) -> EncryptedData:
        """
        Criptografa dados usando chave ativa.

        Args:
            data: Dados para criptografar

        Returns:
            EncryptedData com ciphertext e metadados
        """
        # Verifica se precisa rotacionar
        if self._active_key_id:
            metadata = self._key_metadata.get(self._active_key_id)
            if metadata and metadata.should_rotate():
                self.rotate_key()

        # Criptografa com chave ativa
        fernet = self._keys[self._active_key_id]
        ciphertext = fernet.encrypt(data)

        return EncryptedData(
            ciphertext=ciphertext,
            key_id=self._active_key_id
        )

    def decrypt(self, encrypted: EncryptedData) -> bytes:
        """
        Descriptografa dados usando chave específica.

        Args:
            encrypted: EncryptedData para descriptografar

        Returns:
            Dados originais

        Raises:
            KeyError: Se chave não encontrada
            cryptography.fernet.InvalidToken: Se token inválido
        """
        # Tenta encontrar chave
        if encrypted.key_id not in self._keys:
            # Tenta carregar do disco
            self._load_key_from_disk(encrypted.key_id)

        fernet = self._keys.get(encrypted.key_id)
        if not fernet:
            raise KeyError(f"Chave {encrypted.key_id} não encontrada")

        # Atualiza uso
        if encrypted.key_id in self._key_metadata:
            self._key_metadata[encrypted.key_id].usage_count += 1

        return fernet.decrypt(encrypted.ciphertext)

    def rotate_key(self) -> KeyMetadata:
        """
        Cria nova chave e a torna ativa.

        Returns:
            Metadados da nova chave
        """
        return self._create_new_key()

    def get_key_metadata(self, key_id: Optional[str] = None) -> KeyMetadata:
        """
        Retorna metadados de uma chave.

        Args:
            key_id: ID da chave. Se None, retorna chave ativa.
        """
        kid = key_id or self._active_key_id
        if not kid or kid not in self._key_metadata:
            raise KeyError(f"Chave {kid} não encontrada")
        return self._key_metadata[kid]

    def get_active_key_id(self) -> str:
        """Retorna ID da chave ativa."""
        return self._active_key_id

    def _generate_master_key(self) -> bytes:
        """Gera chave mestra de 32 bytes."""
        return os.urandom(32)

    def _save_master_key(self):
        """Salva chave mestra em arquivo (apenas para dev)."""
        if not self.keys_dir:
            return

        self.keys_dir.mkdir(parents=True, exist_ok=True)
        key_file = self.keys_dir / "master.key"

        # Em produção, usar cofre de secretos!
        key_file.write_bytes(self._master_key)
        key_file.chmod(0o600)  # Somente dono lê

    def _generate_key_id(self) -> str:
        """Gera ID único para chave."""
        import uuid
        return f"key_{uuid.uuid4().hex[:16]}"

    def _derive_key(self, key_id: str) -> bytes:
        """
        Deriva chave Fernet da chave mestra + key_id.

        Usa PBKDF2-HMAC-SHA256 para derivação.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=key_id.encode(),
            iterations=100000,
        )
        return kdf.derive(self._master_key)

    def _create_fernet(self, key: bytes) -> Fernet:
        """Cria instância Fernet de chave derivada."""
        # Fernet requer chave de 32 bytes url-safe base64
        fernet_key = base64.urlsafe_b64encode(key)
        return Fernet(fernet_key)

    def _create_new_key(self) -> KeyMetadata:
        """Cria nova chave e a torna ativa."""
        key_id = self._generate_key_id()
        derived_key = self._derive_key(key_id)
        fernet = self._create_fernet(derived_key)

        # Armazena
        self._keys[key_id] = fernet
        self._key_metadata[key_id] = KeyMetadata(
            key_id=key_id,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=self.key_rotation_days),
            is_active=True,
            usage_count=0
        )

        # Desativa chave anterior
        for kid in self._key_metadata:
            if kid != key_id:
                self._key_metadata[kid].is_active = False

        self._active_key_id = key_id

        # Salva se tiver diretório
        if self.keys_dir:
            self._save_key_to_disk(key_id)

        return self._key_metadata[key_id]

    def _save_key_to_disk(self, key_id: str):
        """Salva chave em disco (apenas para persistência local)."""
        if not self.keys_dir:
            return

        keys_file = self.keys_dir / "keys.json"
        import json

        keys_data = {
            kid: meta.to_dict()
            for kid, meta in self._key_metadata.items()
        }

        with open(keys_file, "w") as f:
            json.dump(keys_data, f, indent=2)

    def _load_keys(self):
        """Carrega chaves do disco."""
        if not self.keys_dir:
            return

        keys_file = self.keys_dir / "keys.json"
        if not keys_file.exists():
            return

        import json
        with open(keys_file) as f:
            keys_data = json.load(f)

        for key_id, data in keys_data.items():
            # Recria Fernet
            derived_key = self._derive_key(key_id)
            fernet = self._create_fernet(derived_key)
            self._keys[key_id] = fernet

            # Recria metadata
            self._key_metadata[key_id] = KeyMetadata(
                key_id=data["key_id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
                is_active=data["is_active"],
                usage_count=data["usage_count"],
                max_usages=data["max_usages"]
            )

            # Define ativa
            if data["is_active"]:
                self._active_key_id = key_id

        # Se nenhuma chave ativa, cria nova
        if not self._active_key_id:
            self._create_new_key()

    def _load_key_from_disk(self, key_id: str):
        """Carrega chave específica do disco."""
        if not self.keys_dir:
            raise KeyError(f"keys_dir não configurado")

        keys_file = self.keys_dir / "keys.json"
        if not keys_file.exists():
            raise KeyError(f"Arquivo de chaves não existe")

        import json
        with open(keys_file) as f:
            keys_data = json.load(f)

        if key_id not in keys_data:
            raise KeyError(f"Chave {key_id} não encontrada")

        data = keys_data[key_id]
        derived_key = self._derive_key(key_id)
        fernet = self._create_fernet(derived_key)
        self._keys[key_id] = fernet

        self._key_metadata[key_id] = KeyMetadata(
            key_id=data["key_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data["expires_at"] else None,
            is_active=data["is_active"],
            usage_count=data["usage_count"],
            max_usages=data["max_usages"]
        )


class AuditLogger:
    """
    Audit log para operações de criptografia.

    Registra cada encrypt/decrypt/rotate para compliance.
    """

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, operation: str, key_id: str, details: Optional[dict] = None):
        """
        Registra operação no audit log.

        Args:
            operation: "encrypt", "decrypt", "rotate_key"
            key_id: ID da chave usada
            details: Dict com detalhes adicionais
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "key_id": key_id,
            "details": details or {}
        }

        import json
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")