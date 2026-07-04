-- Script de criação do banco de dados PostgreSQL
-- Execute como superusuário (postgres)
--
-- Uso:
--   psql -U postgres -f setup_postgres.sql
--

-- Cria banco de dados
CREATE DATABASE olho_de_deus
    WITH ENCODING 'UTF8'
    LC_COLLATE = 'pt_BR.UTF-8'
    LC_CTYPE = 'pt_BR.UTF-8'
    TEMPLATE = template0;

-- Cria usuário dedicado (troque 'sua_senha_forte' por uma senha segura)
CREATE USER olho_de_deus_user WITH
    PASSWORD 'sua_senha_forte'
    CREATEDB
    NOCREATEROLE
    NOSUPERUSER;

-- Concede privilégios
GRANT ALL PRIVILEGES ON DATABASE olho_de_deus TO olho_de_deus_user;

-- Conecta ao banco criado
\c olho_de_deus

-- Concede privilégios no schema público
GRANT ALL ON SCHEMA public TO olho_de_deus_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO olho_de_deus_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO olho_de_deus_user;

-- Alter default privileges para futuras tabelas
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON TABLES TO olho_de_deus_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT ALL ON SEQUENCES TO olho_de_deus_user;

-- Extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pgvector";  -- Requer instalação prévia

-- Comentário descritivo
COMMENT ON DATABASE olho_de_deus IS 'Banco de dados do sistema Olho de Deus v3.0';

-- Mensagem de confirmação
DO $$
BEGIN
    RAISE NOTICE '✅ Banco de dados "olho_de_deus" criado com sucesso!';
    RAISE NOTICE '✅ Usuário "olho_de_deus_user" criado!';
    RAISE NOTICE '';
    RAISE NOTICE 'Configure seu .env com:';
    RAISE NOTICE 'DATABASE_URL=postgresql://olho_de_deus_user:sua_senha_forte@localhost:5432/olho_de_deus';
END $$;