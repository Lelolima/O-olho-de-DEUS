"""Dashboard Server - Aplicação FastAPI para o sistema."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento de ciclo de vida da aplicação."""
    # Startup
    logger.info("Iniciando Olho de Deus API v3.0...")

    # Inicializa banco de dados
    db_available = False
    try:
        from sqlalchemy import text

        from src.cloud.database import create_tables, engine

        create_tables()

        # Verifica conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_available = True
        logger.info("Banco de dados inicializado")
    except SQLAlchemyError as e:
        logger.warning(f"Banco de dados não disponível: {e}")
        logger.info("Usando armazenamento em memória como fallback")

    # Inicializa componentes
    from src.cloud.services.fairness_service import fairness_service
    from src.forensic.logger import ForensicLogger

    app.state.forensic_logger = ForensicLogger(
        log_dir=os.environ.get("EVIDENCE_DIR", "./forensic_logs"),
        tsa_enabled=os.environ.get("TSA_ENABLED", "false").lower() == "true",
        tsa_url=os.environ.get("TSA_URL") or None,
    )
    from src.cloud.api.middleware.auth import operator_auth

    if not operator_auth.has_users():
        logger.warning(
            "Nenhum operador configurado: defina OPERATOR_USERS (veja .env.example). O login responderá 503 até lá."
        )
    app.state.fairness_service = fairness_service
    app.state.db_available = db_available

    logger.info("Componentes inicializados")

    yield

    # Shutdown
    logger.info("Fechando aplicação...")

    # Fecha recursos
    if hasattr(app.state, "forensic_logger"):
        app.state.forensic_logger.flush_batch()


def create_app() -> FastAPI:
    """Factory para criar aplicação FastAPI."""

    app = FastAPI(
        title="Olho de Deus API",
        description="Sistema de vigilância com IA - Edge-to-Cloud com conformidade LGPD",
        version="3.0.0",
        lifespan=lifespan,
    )

    # CORS middleware
    origins = _cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # CORS_ORIGINS (vírgulas); "*" desliga credenciais
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"{request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response: {response.status_code}")
        return response

    # Inclui routers
    from src.cloud.api.middleware.auth import operator_auth
    from src.cloud.api.routes import alerts, evidence, hitl

    app.include_router(alerts.router)
    app.include_router(hitl.router)
    app.include_router(evidence.router)

    # Rotas de autenticação
    from fastapi import Depends, HTTPException
    from fastapi.security import OAuth2PasswordRequestForm

    @app.post("/api/v1/auth/token")
    async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
        """Obtém token JWT de operador (limitado por IP contra força bruta)."""
        from src.cloud.api.middleware.rate_limiter import login_rate_limiter

        client_ip = request.client.host if request.client else "desconhecido"
        allowed, details = login_rate_limiter.is_allowed(f"login:{client_ip}")
        if not allowed:
            retry = 3600 if details.get("reason") == "hour_limit_exceeded" else 60
            logger.warning(f"Login bloqueado por excesso de tentativas: {client_ip}")
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas de login. Tente novamente mais tarde.",
                headers={"Retry-After": str(retry)},
            )
        if not operator_auth.has_users():
            raise HTTPException(
                status_code=503,
                detail="Nenhum operador configurado no servidor. Defina OPERATOR_USERS (veja .env.example).",
            )
        operator = operator_auth.authenticate(form_data.username, form_data.password)
        if not operator:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        token = operator_auth.create_token(operator["username"], operator["role"])
        return {"access_token": token, "token_type": "bearer"}

    # Health check
    @app.get("/health")
    async def health_check():
        """Verifica saúde da API."""
        from sqlalchemy import text

        from src.cloud.database import engine

        status = {"status": "healthy", "version": "3.0.0", "database": "unknown"}

        # Verifica banco de dados
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status["database"] = "connected"
        except SQLAlchemyError as e:
            status["database"] = f"disconnected: {str(e)[:50]}"
            status["status"] = "degraded"

        # Verifica forensic logger
        if hasattr(app.state, "forensic_logger"):
            status["forensic_logger"] = "active"
        else:
            status["forensic_logger"] = "inactive"

        return status

    # API info
    @app.get("/")
    async def root():
        """Informações da API."""
        return {"name": "Olho de Deus API", "version": "3.0.0", "docs": "/docs", "health": "/health"}

    return app


# Cria instância da aplicação
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("API_HOST", "127.0.0.1"), port=int(os.environ.get("API_PORT", "8000")))
