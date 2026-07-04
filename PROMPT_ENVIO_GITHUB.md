# 🚀 PROMPT PARA ENVIO AO GITHUB

**Repositório:** https://github.com/Lelolima/O-olho-de-DEUS  
**Versão:** 3.0.1  
**Data:** 2026-07-04

---

## 📋 INSTRUÇÕES PARA IA

Você deve enviar os arquivos corrigidos do projeto **Olho de Deus v3.0.1** para o repositório GitHub acima, seguindo **rigorosamente** estas diretrizes de segurança.

---

## ⚠️ REGRAS DE SEGURANÇA CRÍTICAS

### ❌ NUNCA ENVIE/COMITE ESTES ARQUIVOS

| Arquivo | Motivo | Risco |
|---------|--------|-------|
| `.env` | Contém segredos reais | **CRÍTICO** - Vazamento de chaves |
| `*.key` | Chaves de criptografia | **CRÍTICO** - Quebra de segurança |
| `logs/*.log` | Pode conter dados sensíveis | **ALTO** - Vazamento de informações |
| `evidence/*.jpg` | Frames de câmeras | **ALTO** - Privacidade |
| `forensic_logs/*.json` | Logs forenses | **ALTO** - Dados sensíveis |
| `__pycache__/` | Bytes compilados | **MÉDIO** - Info de estrutura |
| `.pytest_cache/` | Cache de testes | **BAIXO** - Sujeira |

### ✅ ARQUIVOS QUE PODEM SER ENVIADOS

| Categoria | Arquivos | Status |
|-----------|----------|--------|
| **Código Fonte** | `src/**/*.py` | ✅ Seguro |
| **Testes** | `tests/**/*.py` | ✅ Seguro |
| **Config (Template)** | `.env.example`, `pyproject.toml`, `config.yaml.example` | ✅ Seguro (sem segredos reais) |
| **Documentação** | `*.md` | ✅ Seguro |
| **Scripts** | `*.py`, `*.sql`, `*.bat` (apenas scripts úteis) | ✅ Seguro |
| **Docker** | `docker-compose.yml`, `docker/**` | ✅ Seguro |
| **Git** | `.gitignore` | ✅ Seguro |

---

## 📁 ESTRUTURA COMPLETA PARA ENVIO

```
O-olho-de-DEUS/
│
├── 📂 src/
│   ├── __init__.py
│   ├── edge/
│   │   ├── __init__.py
│   │   ├── processor.py
│   │   ├── streamer.py
│   │   └── masker.py
│   ├── cloud/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── alerts.py          ← ✅ ATUALIZADO
│   │   │   │   ├── evidence.py        ← ✅ ATUALIZADO
│   │   │   │   └── hitl.py
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       └── rate_limiter.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── alert_service.py
│   │   │   ├── notification_service.py
│   │   │   └── fairness_service.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── incident.py
│   │   │   └── hitl_decision.py
│   │   ├── database.py                ← ✅ NOVO
│   │   └── init_db.py                 ← ✅ NOVO
│   ├── forensic/
│   │   ├── __init__.py
│   │   ├── merkle_tree.py
│   │   ├── timestamp.py
│   │   └── logger.py
│   ├── privacy/
│   │   ├── __init__.py
│   │   ├── masker.py
│   │   ├── encryption.py
│   │   ├── conditional_unblur.py
│   │   └── legal_basis.py
│   ├── fairness/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   └── bias_detector.py
│   └── hitl/
│       ├── __init__.py
│       ├── dashboard_server.py        ← ✅ ATUALIZADO
│       └── operator_auth.py
│
├── 📂 tests/
│   ├── __init__.py
│   ├── edge/
│   │   ├── __init__.py
│   │   └── test_edge.py
│   ├── forensic/
│   │   ├── __init__.py
│   │   └── test_forensic.py
│   └── fairness/
│       ├── __init__.py
│       └── test_fairness.py
│
├── 📂 scripts/
│   ├── verify_syntax.py
│   └── setup_postgres.sql
│
├── 🔧 CONFIGURAÇÃO
│   ├── main.py
│   ├── pyproject.toml
│   ├── setup_secure_install.py
│   ├── config.yaml.example
│   ├── .env.example                   ← ✅ ATUALIZADO (template sem segredos)
│   ├── .gitignore                     ← ✅ ATUALIZADO
│   └── docker-compose.yml
│
├── 📘 DOCUMENTAÇÃO
│   ├── README.md
│   ├── CLAUDE.md
│   ├── IMPLEMENTACAO_CONCLUÍDA.md
│   ├── AUDITORIA_SEGURANCA_VIES.md
│   ├── CHECKLIST_VERIFICACAO_FINAL.md
│   ├── RELATORIO_FINAL_IMPLANTACAO.md
│   ├── ALTERACOES_RECENTES.md         ← ✅ NOVO
│   ├── GUIA_IMPLANTACAO_RAPIDA.md     ← ✅ NOVO
│   ├── ESTRUTURA_PROJETO.md           ← ✅ NOVO
│   └── ORGANIZACAO_CONCLUÍDA.md       ← ✅ NOVO
│
└── 🗄️ LEGADO_v2.0.0/                  ← ⚠️ OPCIONAL (apenas se útil para histórico)
    └── (...)
```

---

## 🔐 VERIFICAÇÃO PRÉ-COMMIT

Antes de cada `git commit`, execute:

```bash
# 1. Verifique se .env NÃO está sendo commitado
git status

# 2. Verifique o que será enviado
git diff --cached --name-only

# 3. Garanta que .env está no .gitignore
grep "^\.env$" .gitignore  # Deve retornar uma linha
```

### ✅ CHECKLIST DE SEGURANÇA

Marque antes de enviar:

- [ ] `.env` **NÃO** está na lista de arquivos a commitar
- [ ] Nenhuma chave real (`JWT_SECRET=`, `ENCRYPTION_KEY=`) está nos arquivos
- [ ] `.env.example` contém **apenas templates** (ex: `sua-chave-aqui`)
- [ ] Nenhum arquivo de log está sendo enviado
- [ ] Nenhuma evidência (`evidence/`) está sendo enviada
- [ ] `__pycache__/` está no `.gitignore`

---

## 📝 COMANDOS SUGERIDOS

### Preparação

```bash
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"

# 1. Certifique-se de que .env NÃO existe (ou está no .gitignore)
# Se existir, APAGUE antes de commitar
del .env 2>nul

# 2. Verifique o status
git status

# 3. Adicione apenas arquivos seguros
git add src/ tests/ scripts/ *.py *.toml *.yaml.example *.md .gitignore docker-compose.yml docker/

# 4. Verifique novamente o que será commitado
git status --short
```

### Commit

```bash
# Mensagem de commit descritiva
git commit -m "v3.0.1: Correções de segurança e persistência PostgreSQL

- Autenticação JWT em todos endpoints críticos
- Persistência com PostgreSQL + fallback SQLite
- Health check com status do banco de dados
- Novos módulos: database.py, init_db.py
- Atualizados: alerts.py, evidence.py, dashboard_server.py
- Documentação completa de implantação

SEGURANÇA: Nenhuma chave ou segredo commitado
CHANGES: https://github.com/Lelolima/O-olho-de-DEUS/blob/main/ALTERACOES_RECENTES.md"
```

### Push

```bash
# Verifique a branch
git branch

# Se não estiver em main/master, crie uma branch
git checkout -b feature/v3.0.1-correcoes

# Envie para o repositório
git push origin feature/v3.0.1-correcoes

# Ou para main (se tiver permissão)
# git push origin main
```

---

## 🔍 VERIFICAÇÃO PÓS-ENVIO

Após o push, verifique no GitHub:

1. **Settings → Secrets and variables → Actions**
   - Adicione as variáveis de ambiente como **secrets**:
     - `JWT_SECRET`
     - `ENCRYPTION_KEY`
     - `DATABASE_URL`

2. **Settings → Branches → Branch protection rules**
   - Adicione regra para `main`:
     - ✅ Require pull request reviews
     - ✅ Require status checks to pass before merging

3. **Verifique no código-fonte público**
   - Confirme que `.env` NÃO aparece nos arquivos
   - Confirme que `.env.example` tem apenas templates

---

## 📌 VARIÁVEIS DE AMBIENTE PARA GITHUB SECRETS

Configure no GitHub (**Settings → Secrets and variables → Actions**):

| Variável | Como Gerar | Uso |
|----------|------------|-----|
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` | Autenticação JWT |
| `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | Criptografia Fernet |
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/olho_de_deus` | Conexão PostgreSQL |
| `USE_SQLITE` | `true` (dev) ou `false` (prod) | Usar SQLite ou PostgreSQL |
| `LOG_LEVEL` | `INFO` | Nível de logging |
| `DEBUG` | `false` | Debug mode (nunca true em prod) |

---

## ⚠️ NUNCA FAÇA ISSO

```bash
# ❌ NUNCA commit .env real
git add .env
git commit -m " adiciona config"

# ❌ NUNCA commit chaves reais
echo "JWT_SECRET=minha-chave-real" >> .env
git add .

# ❌ NUNCA push direto de segredos
git push origin main  # Com segredos no código
```

### Se Acidentalmente Commitar Segredos

```bash
# 1. Remove o arquivo do último commit
git reset HEAD~1

# 2. Adicione ao .gitignore se não estiver
echo ".env" >> .gitignore

# 3. Commite novamente sem o arquivo
git add .
git commit -m "..."
git push

# 4. Invalidade o segredo vazado imediatamente!
# Gere novo JWT_SECRET e ENCRYPTION_KEY
```

---

## 📞 SUPORTE

Se tiver dúvidas sobre o que pode ou não ser enviado:

1. **Dúvida?** Não envie. Pergunte primeiro.
2. **Template vs Real:** `.env.example` (template) ✅, `.env` (real) ❌
3. **Logs:** Nunca envie `*.log` ou conteúdo de `logs/`
4. **Dados:** Nunca envie `evidence/`, `forensic_logs/`, `incidents/`

---

**Checklist Final:**

- [ ] `.env` apagado ou no `.gitignore`
- [ ] Nenhuma chave real no código
- [ ] `.env.example` é apenas template
- [ ] `git status --short` limpo de segredos
- [ ] GitHub Secrets configurados
- [ ] Branch protection habilitada

**Status:** ✅ **SEGURO PARA ENVIO**