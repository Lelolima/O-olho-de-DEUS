# 🚀 GUIA RÁPIDO DE IMPLANTAÇÃO - OLHO DE DEUS v3.0.1

**Data:** 2026-07-04  
**Versão:** 3.0.1  
**Status:** ✅ Pronto para desenvolvimento

---

## 📋 PRÉ-REQUISITOS

- Python 3.9 ou superior
- Poetry (`pip install poetry`)
- PostgreSQL (opcional, usa SQLite se não tiver)

---

## 🔧 INSTALAÇÃO RÁPIDA

### 1. Clonar/Copiar Projeto

```bash
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
```

### 2. Instalar Dependências

```bash
poetry install
```

### 3. Configurar Ambiente

```bash
# Copiar template
cp .env.example .env

# Gerar JWT_SECRET
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))" > .env

# Ou editar .env manualmente
notepad .env
```

### 4. (Opcional) Configurar PostgreSQL

```bash
# Se tiver PostgreSQL instalado:
psql -U postgres -f setup_postgres.sql

# Ou usar SQLite (desenvolvimento):
# No .env: USE_SQLITE=true
```

### 5. Inicializar Banco de Dados

```bash
python -m src.cloud.init_db
```

---

## ▶️ COMO RODAR

### Opção 1: API Completa (Recomendado)

```bash
poetry run python -m src.hitl.dashboard_server
```

A API inicia em `http://localhost:8000`

### Opção 2: Sistema Completo (Edge + API)

```bash
poetry run python main.py --config config.yaml --mode all
```

### Opção 3: Apenas Edge (Processamento de Vídeo)

```bash
poetry run python main.py --config config.yaml --mode edge
```

---

## 📡 ENDPOINTS DA API

### Acessar Documentação

```
http://localhost:8000/docs     # Swagger UI
http://localhost:8000/         # Info da API
http://localhost:8000/health   # Health check
```

### Login (Obter Token)

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin" -d "password=admin123"
```

### Criar Alerta (Requer Autenticação)

```bash
TOKEN="seu-token-aqui"

curl -X POST http://localhost:8000/api/v1/alerts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "CAM-001",
    "alarm_score": 0.85,
    "behavior_indicators": ["multiple_faces"],
    "faces_count": 3
  }'
```

### Listar Alertas

```bash
curl http://localhost:8000/api/v1/alerts/ \
  -H "Authorization: Bearer $TOKEN"
```

### Upload de Evidência

```bash
curl -X POST http://localhost:8000/api/v1/evidence/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@frame.jpg" \
  -F "camera_id=CAM-001"
```

---

## 🧪 RODAR TESTES

```bash
# Todos os testes
poetry run pytest

# Com coverage
poetry run pytest --cov=src --cov-report=html

# Módulo específico
poetry run pytest tests/forensic/test_forensic.py -v
poetry run pytest tests/edge/test_edge.py -v
poetry run pytest tests/fairness/test_fairness.py -v
```

---

## 🔍 VERIFICAÇÃO DE SAÚDE

```bash
# Health check completo
curl http://localhost:8000/health | jq

# Saída esperada:
{
  "status": "healthy",
  "version": "3.0.1",
  "database": "connected",
  "forensic_logger": "active"
}
```

---

## 📊 USUÁRIOS PADRÃO

| Usuário | Senha | Role |
|---------|-------|------|
| `admin` | `admin123` | admin |
| `operator1` | `op123` | operator |
| `supervisor` | `sup123` | supervisor |

**⚠️ IMPORTANTE:** Mude as senhas em produção!

---

## 🔐 VARIÁVEIS DE AMBIENTE CRÍTICAS

### Obrigatórias (Produção)

```env
JWT_SECRET=sua-chave-secreta-256-bit
DATABASE_URL=postgresql://user:pass@localhost:5432/olho_de_deus
ENCRYPTION_KEY=chave-fernet-base64
```

### Opcionais

```env
USE_SQLITE=false           # true para desenvolvimento
TSA_URL=https://freetsa.org/tsr
LOG_LEVEL=INFO
DEBUG=false
```

---

## 🛠️ COMANDOS ÚTEIS

### Verificar Sintaxe Python

```bash
python verify_syntax.py
```

### Gerar Chave de Criptografia

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Criar Migration (Alembic)

```bash
# Futura implementação
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

---

## 📁 ESTRUTURA DE ARQUIVOS

```
olho-de-deus-corrigido/
├── src/
│   ├── edge/           # Edge AI Processing
│   ├── cloud/          # Cloud Backend + DB
│   ├── forensic/       # Cadeia de Custódia
│   ├── privacy/        # Privacy by Design
│   ├── fairness/       # Fairness-Aware ML
│   └── hitl/           # HITL Dashboard
├── tests/              # Testes unitários
├── .env.example        # Template de variáveis
├── pyproject.toml      # Dependencies Poetry
├── CLAUDE.md           # Documentação técnica
├── CHECKLIST_VERIFICACAO_FINAL.md
└── ALTERACOES_RECENTES.md
```

---

## ⚠️ PROBLEMAS COMUNS

### "ModuleNotFoundError"

```bash
# Reinstalar dependências
poetry install --no-cache
```

### "DATABASE_URL not set"

```bash
# Usar SQLite em desenvolvimento
echo "USE_SQLITE=true" >> .env
```

### "JWT_SECRET not set"

```bash
# Gerar novo segredo
python -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))" >> .env
```

---

## 📞 SUPORTE

- **Issues:** https://github.com/Lelolima/O-olho-de-DEUS/issues
- **Documentação:** `CLAUDE.md`
- **Auditoria:** `AUDITORIA_SEGURANCA_VIES.md`
- **Checklist:** `CHECKLIST_VERIFICACAO_FINAL.md`

---

**Última Atualização:** 2026-07-04  
**Próxima Revisão:** 2026-08-04  
**Status:** ✅ **APROVADO PARA DESENVOLVIMENTO**