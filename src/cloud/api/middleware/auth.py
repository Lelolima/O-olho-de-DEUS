"""API Middleware - Autenticação, logging e CORS."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
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


class OperatorAuth:
    """
    Autenticação de operadores HITL.

    Em produção, integrar com:
    - OAuth2 (Google, Microsoft Entra ID)
    - LDAP/Active Directory
    - Banco de dados de usuários
    """

    def __init__(self, secret: str = JWT_SECRET):
        self.secret = secret

        # Usuários mock (em produção, usar banco de dados)
        self._users = {
            "admin": {"password": "admin123", "role": "admin"},
            "operator1": {"password": "op123", "role": "operator"},
            "supervisor": {"password": "sup123", "role": "supervisor"}
        }

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Verifica credenciais."""
        user = self._users.get(username)
        if user and user["password"] == password:
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


async def get_current_operator(token: str = oauth2_scheme) -> dict:
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


async def require_role(required_role: str):
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


# Import necessário para o dependency
from fastapi import Depends