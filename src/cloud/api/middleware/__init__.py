"""Middleware __init__."""

from src.cloud.api.middleware.auth import (
    JWT_SECRET,  # Exportado para verificação em testes
    OperatorAuth,
    get_current_operator,
    oauth2_scheme,
    operator_auth,
    require_role,
)
from src.cloud.api.middleware.rate_limiter import RateLimitMiddleware, rate_limit_decorator, rate_limiter

__all__ = [
    "JWT_SECRET",
    "OperatorAuth",
    "RateLimitMiddleware",
    "get_current_operator",
    "oauth2_scheme",
    "operator_auth",
    "rate_limit_decorator",
    "rate_limiter",
    "require_role",
]
