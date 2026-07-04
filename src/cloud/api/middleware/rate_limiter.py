"""Rate Limiter Middleware - Proteção contra brute force e DoS."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter estilo token bucket.

    Limita requisições por IP/operador para prevenir:
    - Brute force attacks
    - Denial of Service (DoS)
    - Alert flooding
    """

    def __init__(
        self,
        requests_per_minute: int = 100,
        requests_per_hour: int = 1000,
        burst_size: int = 20
    ):
        """
        Inicializa rate limiter.

        Args:
            requests_per_minute: Máximo de requisições por minuto
            requests_per_hour: Máximo de requisições por hora
            burst_size: Tamanho do burst permitido (para picos curtos)
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size

        # Armazena timestamps de requisições por identificador
        self._requests: Dict[str, List[datetime]] = defaultdict(list)

        # Limpeza automática a cada N minutos
        self._cleanup_interval = timedelta(minutes=5)
        self._last_cleanup = datetime.now()

    def is_allowed(self, identifier: str) -> Tuple[bool, dict]:
        """
        Verifica se requisição é permitida para identificador.

        Args:
            identifier: IP, user_id, ou outro identificador

        Returns:
            Tuple (permitida, detalhes)
        """
        now = datetime.now()

        # Limpa registros antigos periodicamente
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_requests()
            self._last_cleanup = now

        # Filtra requisições dentro das janelas
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        recent_requests = self._requests[identifier]
        requests_last_minute = sum(1 for r in recent_requests if r > minute_ago)
        requests_last_hour = sum(1 for r in recent_requests if r > hour_ago)

        # Verifica limites
        details = {
            "requests_last_minute": requests_last_minute,
            "requests_last_hour": requests_last_hour,
            "limit_minute": self.requests_per_minute,
            "limit_hour": self.requests_per_hour
        }

        # Burst allowance para primeiros requests
        if len(recent_requests) < self.burst_size:
            self._requests[identifier].append(now)
            return True, {**details, "burst_remaining": self.burst_size - len(recent_requests)}

        # Verifica limite por minuto
        if requests_last_minute >= self.requests_per_minute:
            return False, {**details, "reason": "minute_limit_exceeded"}

        # Verifica limite por hora
        if requests_last_hour >= self.requests_per_hour:
            return False, {**details, "reason": "hour_limit_exceeded"}

        # Permite requisição
        self._requests[identifier].append(now)
        return True, {**details, "allowed": True}

    def _cleanup_old_requests(self):
        """Remove requests mais antigos que 1 hora."""
        hour_ago = datetime.now() - timedelta(hours=1)

        for identifier in list(self._requests.keys()):
            self._requests[identifier] = [
                r for r in self._requests[identifier]
                if r > hour_ago
            ]

            # Remove chaves vazias
            if not self._requests[identifier]:
                del self._requests[identifier]


# Rate limiter global
rate_limiter = RateLimiter(
    requests_per_minute=100,
    requests_per_hour=1000,
    burst_size=20
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware FastAPI para rate limiting baseado em IP.

    Uso:
        app.add_middleware(RateLimitMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        # Extrai IP do cliente
        client_ip = request.client.host

        # Endpoints isentos de rate limiting
        exempt_paths = ["/health", "/", "/docs", "/openapi.json"]
        if request.url.path in exempt_paths:
            return await call_next(request)

        # Verifica rate limit
        allowed, details = rate_limiter.is_allowed(client_ip)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_ip}: {details}")

            # Determina tempo de retry baseado no limite excedido
            if details.get("reason") == "hour_limit_exceeded":
                retry_after = 3600  # 1 hora
            else:
                retry_after = 60  # 1 minuto

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": details,
                    "retry_after_seconds": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        # Adiciona headers de rate limit na resposta
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            details["limit_minute"] - details["requests_last_minute"]
        )
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            details["limit_hour"] - details["requests_last_hour"]
        )

        return response


def rate_limit_decorator(requests_per_minute: int = 60):
    """
    Decorator para rate limiting em rotas específicas.

    Uso:
        @router.post("/alerts")
        @rate_limit_decorator(requests_per_minute=10)
        async def create_alert(...):
            ...
    """
    limiter = RateLimiter(requests_per_minute=requests_per_minute)

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            identifier = f"{request.client.host}:{func.__name__}"
            allowed, details = limiter.is_allowed(identifier)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {details}"
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator