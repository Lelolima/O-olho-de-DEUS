"""Dashboard Server - Aplicação FastAPI para o sistema."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento de ciclo de vida da aplicação."""
    # Startup
    logger.info("Iniciando Olho de Deus API v3.0...")

    # Inicializa banco de dados
    db_available = False
    try:
        from src.cloud.database import create_tables, engine
        from sqlalchemy import text

        create_tables()

        # Verifica conexão
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_available = True
        logger.info("✅ Banco de dados inicializado")
    except Exception as e:
        logger.warning(f"⚠️ Banco de dados não disponível: {e}")
        logger.info("Usando armazenamento em memória como fallback")

    # Inicializa componentes
    from src.forensic.logger import ForensicLogger
    from src.cloud.services.fairness_service import fairness_service

    app.state.forensic_logger = ForensicLogger(
        log_dir="./forensic_logs",
        tsa_enabled=True
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
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, especificar origens permitidas
        allow_credentials=True,
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
    from src.cloud.api.routes import alerts, hitl, evidence
    from src.cloud.api.middleware.auth import operator_auth

    app.include_router(alerts.router)
    app.include_router(hitl.router)
    app.include_router(evidence.router)

    # Rotas de autenticação
    from fastapi import Depends, HTTPException
    from fastapi.security import OAuth2PasswordRequestForm

    @app.post("/api/v1/auth/token")
    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        """Obtém token JWT de operador."""
        operator = operator_auth.authenticate(form_data.username, form_data.password)
        if not operator:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        token = operator_auth.create_token(
            operator["username"],
            operator["role"]
        )
        return {"access_token": token, "token_type": "bearer"}

    # Health check
    @app.get("/health")
    async def health_check():
        """Verifica saúde da API."""
        from src.cloud.database import engine
        from sqlalchemy import text

        status = {
            "status": "healthy",
            "version": "3.0.0",
            "database": "unknown"
        }

        # Verifica banco de dados
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            status["database"] = "connected"
        except Exception as e:
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
        return {
            "name": "Olho de Deus API",
            "version": "3.0.0",
            "docs": "/docs",
            "health": "/health"
        }

    return app


# Cria instância da aplicação
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)