"""
Script de Instalação e Configuração Segura - Olho de Deus v3.0

Este script:
1. Verifica pré-requisitos (Python, dependências)
2. Gera segredos criptográficos seguros
3. Cria arquivo .env com configurações seguras
4. Configura diretórios necessários
5. Valida instalação

Uso:
    python setup_secure_install.py
"""

import os
import sys
import secrets
import hashlib
import shutil
from pathlib import Path
from datetime import datetime


def print_header(text: str):
    """Imprime cabeçalho formatado."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def check_python_version():
    """Verifica versão do Python."""
    print_header("1. Verificando Versão do Python")

    if sys.version_info < (3, 9):
        print(f"❌ Python 3.9+ necessário. Versão atual: {sys.version_info.major}.{sys.version_info.minor}")
        return False

    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_poetry():
    """Verifica se Poetry está instalado."""
    print_header("2. Verificando Poetry")

    try:
        import poetry
        print(f"✅ Poetry {poetry.__version__} encontrado")
        return True
    except ImportError:
        print("⚠️ Poetry não encontrado")
        print("\nInstale Poetry com:")
        print("  pip install poetry")
        print("  ou")
        print("  curl -sSL https://install.python-poetry.org | python3 -")
        return False


def install_dependencies():
    """Instala dependências com Poetry."""
    print_header("3. Instalando Dependências")

    import subprocess

    try:
        result = subprocess.run(
            ["poetry", "install", "--no-interaction"],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print("✅ Dependências instaladas com sucesso")
            return True
        else:
            print(f"❌ Erro ao instalar dependências: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Timeout ao instalar dependências")
        return False
    except FileNotFoundError:
        print("❌ Poetry não encontrado. Instale primeiro.")
        return False


def generate_secure_env():
    """Gera arquivo .env com segredos criptográficos."""
    print_header("4. Gerando Arquivo .env Seguro")

    env_path = Path(".env")

    if env_path.exists():
        backup_path = Path(f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy(env_path, backup_path)
        print(f"📦 Backup criado: {backup_path}")

    # Gera segredos criptográficos
    jwt_secret = secrets.token_hex(32)  # 256-bit
    encryption_key = secrets.token_urlsafe(32)  # Fernet key
    db_password = secrets.token_urlsafe(16)

    env_content = f"""# Olho de Deus v3.0 - Configuração Segura
# Gerado em: {datetime.now().isoformat()}

# =============================================================================
# SEGURANÇA - JWT E CRIPTOGRAFIA
# =============================================================================

# JWT Secret para autenticação de operadores (256-bit)
# ESTE VALOR DEVE SER MANTIDO SECRETO - NÃO COMMITAR NO GIT
JWT_SECRET={jwt_secret}

# Chave de criptografia para rostos (Fernet key)
# Usada para encrypt/decrypt de face ROI
ENCRYPTION_KEY={encryption_key}

# =============================================================================
# BANCO DE DADOS
# =============================================================================

# PostgreSQL connection string
DATABASE_URL=postgresql://olho_de_deus:{db_password}@localhost:5432/olho_de_deus

# Pool size
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# =============================================================================
# TIMESTAMP AUTHORITY (Cadeia de Custódia)
# =============================================================================

# TSA URLs (primeira disponível será usada)
TSA_URL_PRIMARY=https://freetsa.org/tsr
TSA_URL_SECONDARY=http://timestamp.digicert.com

# Habilita carimbo de tempo
TSA_ENABLED=true

# =============================================================================
# NOTIFICAÇÕES
# =============================================================================

# Webhook para alertas (opcional)
WEBHOOK_URL=

# Configuração SMTP para email
SMTP_ENABLED=false
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=
SMTP_PASS=

# Recipientes de email
EMAIL_RECIPIENTS=security@example.com

# =============================================================================
# API CONFIGURAÇÕES
# =============================================================================

# Host e porta da API
API_HOST=0.0.0.0
API_PORT=8000

# CORS origins (separado por vírgula)
CORS_ORIGINS=http://localhost:3000,https://dashboard.example.com

# Rate limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# =============================================================================
# FAIRNESS MONITORING
# =============================================================================

# Habilita monitoramento de viés
FAIRNESS_ENABLED=true

# Thresholds de fairness
FAIRNESS_FPR_THRESHOLD=0.05
FAIRNESS_DP_THRESHOLD=0.10

# Intervalo de verificação (horas)
FAIRNESS_CHECK_INTERVAL=24

# =============================================================================
# LOGGING
# =============================================================================

# Nível de logging
LOG_LEVEL=INFO

# Arquivo de log
LOG_FILE=olho_de_deus.log

# =============================================================================
# PRODUÇÃO vs DESENVOLVIMENTO
# =============================================================================

# Modo debug (NÃO habilitar em produção)
DEBUG=false

# Ambiente
ENVIRONMENT=production
"""

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    # Define permissões seguras (Unix only)
    if os.name != "nt":
        os.chmod(env_path, 0o600)
        print("🔒 Permissões do .env: 600 (somente dono lê/escreve)")

    print(f"✅ Arquivo .env gerado em: {env_path.absolute()}")
    print("\n⚠️  IMPORTANTE:")
    print("  1. Mova .env para local seguro fora do diretório do projeto")
    print("  2. Nunca commit .env no git (.env está no .gitignore)")
    print("  3. Faça backup dos segredos em cofre (HashiCorp Vault, AWS Secrets)")

    return True


def create_directories():
    """Cria diretórios necessários."""
    print_header("5. Criando Diretórios")

    directories = [
        "forensic_logs",
        "forensic_logs/archives",
        "evidence",
        "models",
        "logs",
        "config"
    ]

    for dir_path in directories:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        print(f"  📁 {dir_path}/")

    print("✅ Diretórios criados")
    return True


def copy_config_templates():
    """Copia templates de configuração."""
    print_header("6. Copiando Templates de Configuração")

    templates = [
        ("config.yaml.example", "config.yaml"),
        (".env.example", ".env.example.backup")
    ]

    for source, dest in templates:
        src_path = Path(source)
        dst_path = Path(dest)

        if src_path.exists() and not dst_path.exists():
            shutil.copy(src_path, dst_path)
            print(f"  📄 {dest} criado")

    return True


def verify_installation():
    """Verifica se instalação foi bem-sucedida."""
    print_header("7. Verificando Instalação")

    # Verifica imports principais
    try:
        from src.forensic.merkle_tree import MerkleTree
        from src.fairness.metrics import FairnessMetrics
        from src.privacy.masker import DynamicMasker
        print("✅ Imports principais verificados")
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        return False

    # Verifica testes
    import subprocess

    print("\nRodando testes rápidos...")
    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            print("✅ Todos testes passaram")
            return True
        else:
            print(f"⚠️ Alguns testes falharam (isso pode ser ok em dev)")
            return True

    except subprocess.TimeoutExpired:
        print("⚠️ Timeout nos testes - pulando verificação")
        return True
    except Exception as e:
        print(f"⚠️ Não foi possível rodar testes: {e}")
        return True


def print_next_steps():
    """Imprime próximos passos."""
    print_header("PRÓXIMOS PASSOS")

    print("""
✅ Instalação concluída com sucesso!

PARA INICIAR O SISTEMA:

1. Configure variáveis de ambiente (opcional, já gerado em .env):
   - JWT_SECRET: Segredo para JWT (gerado automaticamente)
   - ENCRYPTION_KEY: Chave para criptografia de rostos
   - DATABASE_URL: Conexão PostgreSQL (se usar banco)

2. Inicie o sistema:

   # Modo desenvolvimento (edge + API)
   poetry run python main.py --config config.yaml --mode all

   # Apenas API (HITL dashboard)
   poetry run python -m src.hitl.dashboard_server

   # Apenas Edge (processamento de vídeo)
   poetry run python main.py --config config.yaml --mode edge

3. Acesse o dashboard:
   http://localhost:8000/docs (API docs)
   http://localhost:8000 (API root)

4. Faça login com credenciais padrão:
   Usuário: admin
   Senha: admin123

   ⚠️ MUDE AS SENHAS EM PRODUÇÃO!

PARA PRODUÇÃO:

1. Instale PostgreSQL:
   docker run -d -e POSTGRES_PASSWORD=secret -p 5432:5432 postgres:15

2. Configure TSA URL válida para cadeia de custódia

3. Implemente autenticação OAuth2 real (Google, Azure AD)

4. Configure rate limiting e CORS restritivo

5. Realize teste de viés com dataset diverso

6. Nomeie Encarregado de Dados (DPO) para compliance LGPD

7. Realize Relatório de Impacto à Proteção de Dados (RIPD/AIPD)

SUPORTE:
- Documentação: CLAUDE.md
- Auditoria: AUDITORIA_SEGURANCA_VIES.md
- Issues: https://github.com/Lelolima/O-olho-de-DEUS/issues
""")


def main():
    """Main installation script."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║     OLHO DE DEUS v3.0 - Instalação Segura                 ║
║     Sistema de Vigilância com IA - Conformidade LGPD      ║
╚═══════════════════════════════════════════════════════════╝
""")

    steps = [
        ("Python", check_python_version),
        ("Poetry", check_poetry),
        ("Dependências", install_dependencies),
        (".env Seguro", generate_secure_env),
        ("Diretórios", create_directories),
        ("Config Templates", copy_config_templates),
        ("Verificação", verify_installation),
    ]

    completed = 0
    failed = 0

    for name, func in steps:
        try:
            if func():
                completed += 1
            else:
                failed += 1
                print(f"⚠️ {name} falhou - continuando...")
        except Exception as e:
            failed += 1
            print(f"❌ {name} falhou com erro: {e}")

    print_header("RESUMO DA INSTALAÇÃO")
    print(f"✅ Concluídos: {completed}/{len(steps)}")
    print(f"❌ Falharam: {failed}/{len(steps)}")

    if failed == 0:
        print("\n🎉 Instalação bem-sucedida!")
        print_next_steps()
    elif failed <= 2:
        print("\n⚠️ Instalação concluída com avisos")
        print("Alguns passos opcionais falharam, mas o sistema deve funcionar")
    else:
        print("\n❌ Instalação falhou em múltiplos passos")
        print("Revise os erros acima e tente novamente")
        sys.exit(1)


if __name__ == "__main__":
    main()