# 🚀 GUIA RÁPIDO - ENVIO PARA GITHUB

**Repositório:** https://github.com/Lelolima/O-olho-de-DEUS

---

## ⚡ PASSO A PASSO RÁPIDO

### 1. Verifique Segurança

```powershell
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"

# Execute verificação de segurança
.\scripts\verificar-seguranca.ps1
```

### 2. Prepare Arquivos

```powershell
# Certifique-se que .env NÃO existe
if (Test-Path .env) { Remove-Item .env }

# Adicione apenas arquivos seguros
git add src/ tests/ scripts/ *.py *.toml *.yaml.example *.md .gitignore docker-compose.yml
```

### 3. Commit Seguro

```powershell
# Verifique o que será commitado
git status --short

# Faça commit
git commit -m "v3.0.1: Correções de segurança e PostgreSQL

- Autenticação em todos endpoints críticos
- Persistência PostgreSQL com fallback
- Health check com status do DB
- Novos: database.py, init_db.py, scripts/
- Atualizados: alerts.py, evidence.py, dashboard_server.py
- Documentação: ALTERACOES_RECENTES.md, GUIA_IMPLANTACAO_RAPIDA.md

⚠️ SEGURANÇA: Nenhum segredo commitado (.env, chaves, logs)"
```

### 4. Push

```powershell
# Crie branch se necessário
git checkout -b feature/v3.0.1-correcoes

# Envie
git push origin feature/v3.0.1-correcoes
```

---

## 🔐 CONFIGURE GITHUB SECRETS

No GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Nome | Valor Exemplo |
|------|---------------|
| `JWT_SECRET` | `(gerar: python -c "import secrets; print(secrets.token_hex(32))")` |
| `ENCRYPTION_KEY` | `(gerar: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")` |
| `DATABASE_URL` | `postgresql://postgres:senha@localhost:5432/olho_de_deus` |
| `USE_SQLITE` | `true` (dev) ou `false` (prod) |

---

## ❌ NUNCA ENVIE

- `.env` com segredos reais
- `*.key` (chaves de criptografia)
- `*.log` (logs podem ter dados sensíveis)
- `evidence/` (frames de câmeras)
- `forensic_logs/` (logs forenses)
- `__pycache__/` (lixo compilado)

---

## ✅ ARQUIVOS SEGUROS PARA ENVIAR

| ✅ Pode Enviar | ❌ Não Enviar |
|----------------|---------------|
| `src/**/*.py` | `.env` |
| `tests/**/*.py` | `*.key` |
| `.env.example` | `*.log` |
| `*.md` | `evidence/` |
| `pyproject.toml` | `forensic_logs/` |
| `scripts/*.py`, `scripts/*.sql` | `__pycache__/` |

---

## 🛡️ VERIFICAÇÃO FINAL

Antes de `git push`:

```powershell
# 1. Verifique arquivos em staging
git diff --cached --name-only

# 2. Garantir .env não está na lista
git ls-files | findstr /i ".env"  # Não deve retornar nada

# 3. Verifique .gitignore
cat .gitignore | select-string "^\.env$"  # Deve retornar ".env"
```

---

## 📊 RESUMO DOS ARQUIVOS

**Total para envio:** ~84 arquivos (código + documentação)

| Categoria | Arquivos | Status |
|-----------|----------|--------|
| `src/` | 56 | ✅ Enviar |
| `tests/` | 8 | ✅ Enviar |
| `scripts/` | 3 | ✅ Enviar |
| Documentação | 10 | ✅ Enviar |
| Config | 5 | ✅ Enviar |
| `.env` | 1 | ❌ NÃO Enviar |

---

**PRONTO!** Após o push, crie Pull Request no GitHub para revisão.