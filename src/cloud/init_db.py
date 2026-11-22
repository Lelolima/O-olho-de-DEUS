"""
Database Initialization - Inicialização do banco de dados.

Este script cria as tabelas e populate dados iniciais.

Uso:
    python -m src.cloud.init_db
"""

import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cloud.database import create_tables, engine


def main():
    """Inicializa banco de dados."""
    print("=" * 50)
    print("INICIALIZAÇÃO DO BANCO DE DADOS")
    print("=" * 50)
    print()

    print("Criando tabelas...")
    try:
        create_tables()
        print("[OK] Tabelas criadas com sucesso!")
    except SQLAlchemyError as e:
        print(f"[ERRO] Erro ao criar tabelas: {e}")
        print()
        print("Nota: Se estiver usando PostgreSQL, certifique-se de:")
        print("  1. Ter o PostgreSQL instalado e rodando")
        print("  2. Criar o banco de dados: CREATE DATABASE olho_de_deus;")
        print("  3. Configurar DATABASE_URL no .env")
        print()
        print("Fallback para SQLite será usado se USE_SQLITE=true")
        return 1

    print()
    print("Verificando conexão...")
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[OK] Conexão verificada!")
    except SQLAlchemyError as e:
        print(f"[AVISO] Erro na conexão: {e}")

    print()
    print("=" * 50)
    print("Banco de dados pronto para uso!")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
