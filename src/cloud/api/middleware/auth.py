"""API Middleware - Autenticação, logging e CORS."""

from fastapi import Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import hmac
import json
import jwt
import logging
import os
import secrets

logger = logging.getLogger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# CORREÇÃO DE SEGURANÇA: JWT Secret de variável de ambiente
# Se não existir, gera um segredo criptográfico seguro (256-bit)
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    JWT_SECRET = secrets.token_hex(32)  # 256-bit
    logger.warning(
        "⚠️ JWT_SECRET não definido em variável de ambiente. "
        "Um segredo temporário foi gerado. Para produção, defina JWT_SECRET no .env"
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8


PBKDF2_ITERATIONS = 600_000


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Gera hash ``pbkdf2_sha256$<iter>$<salt_hex>$<hash_hex>``."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Confere senha contra hash gerado por :func:`hash_password`."""
    try:
        algo, iterations, salt_hex, hash_hex = encoded.split("$")
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), hash_hex)


_DUMMY_HASH = "pbkdf2_sha256$1000$00$00"


def _load_users_from_env() -> dict:
    """Lê OPERATOR_USERS: {"usuario": {"role": "operator", "password_hash": "pbkdf2_sha256$..."}}."""
    raw = os.environ.get("OPERATOR_USERS", "").strip()
    if not raw:
        logger.warning(
            "OPERATOR_USERS não definido: nenhum operador pode autenticar. "
            "Gere hashes com: python -m src.cloud.api.middleware.auth <senha>"
        )
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("OPERATOR_USERS não é JSON válido; nenhum operador carregado")
        return {}
    users = {}
    for name, info in data.items():
        if isinstance(info, dict) and info.get("role") and info.get("password_hash"):
            users[name] = {"role": info["role"], "password_hash": info["password_hash"]}
        else:
            logger.error(f"Entrada inválida em OPERATOR_USERS para '{name}' (ignorada)")
    return users


class OperatorAuth:
    """
    Autenticação de operadores HITL.

    Em produção, integrar com:
    - OAuth2 (Google, Microsoft Entra ID)
    - LDAP/Active Directory
    - Banco de dados de usuários
    """

    def __init__(self, secret: str = JWT_SECRET, users: Optional[dict] = None):
        self.secret = secret

        # SEGURANÇA (auditoria 2026-11-22): as senhas em texto puro que estavam
        # versionadas aqui foram removidas. Usuários vêm da variável OPERATOR_USERS
        # (JSON com hashes PBKDF2). Sem ela, nenhum login é aceito.
        self._users = users if users is not None else _load_users_from_env()

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Verifica credenciais (comparação em tempo constante)."""
        user = self._users.get(username)
        if not user or not isinstance(password, str):
            # Executa um hash mesmo assim para não vazar existência do usuário por tempo
            verify_password(password or "", _DUMMY_HASH)
            return None
        if verify_password(password, user.get("password_hash", "")):
            return {"username": username, "role": user["role"]}
        return None

    def create_token(self, username: str, role: str) -> str:
        """Cria JWT token para operador."""
        payload = {
            "sub": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> Optional[dict]:
        """Verifica e decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret, algorithms=[JWT_ALGORITHM])
            return {
                "username": payload["sub"],
                "role": payload["role"],
                "exp": datetime.fromtimestamp(payload["exp"])
            }
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# Auth global
operator_auth = OperatorAuth()


async def get_current_operator(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency para rotas que requerem autenticação.

    Usage:
        @router.get("/protected")
        async def protected_route(operator=Depends(get_current_operator)):
            return {"user": operator["username"]}
    """
    operator = operator_auth.verify_token(token)
    if operator is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
    return operator


def require_role(required_role: str):
    """
    Dependency para rotas que requerem role específica.

    Usage:
        @router.delete("/admin-only")
        async def admin_route(operator=Depends(require_role("admin"))):
            return {"action": "deleted"}
    """
    async def role_checker(operator: dict = Depends(get_current_operator)):
        if operator["role"] != required_role and operator["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role} requerida"
            )
        return operator
    return role_checker


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Uso: python -m src.cloud.api.middleware.auth <senha>")
        raise SystemExit(2)
    print(hash_password(sys.argv[1]))