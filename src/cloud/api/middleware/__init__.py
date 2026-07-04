"""Middleware __init__."""

from src.cloud.api.middleware.auth import (
    operator_auth,
    OperatorAuth,
    get_current_operator,
    require_role,
    oauth2_scheme,
    JWT_SECRET  # Exportado para verificação em testes
)

from src.cloud.api.middleware.rate_limiter import (
    rate_limiter,
    RateLimitMiddleware,
    rate_limit_decorator
)

__all__ = [
    "operator_auth",
    "OperatorAuth",
    "get_current_operator",
    "require_role",
    "oauth2_scheme",
    "rate_limiter",
    "RateLimitMiddleware",
    "rate_limit_decorator",
    "JWT_SECRET"
]