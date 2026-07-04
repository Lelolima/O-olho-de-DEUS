# Políticas de Segurança do Projeto Olho de Deus

## 📋 Arquivos que NUNCA devem ser commitados

### Críticos (Risco de Vazamento de Dados)
- `.env` - Contém JWT_SECRET, ENCRYPTION_KEY, DATABASE_URL
- `*.key` - Chaves de criptografia
- `evidence/*` - Frames de câmeras (dados sensíveis)
- `forensic_logs/*` - Logs com dados sensíveis
- `logs/*.log` - Logs podem conter informações vazadas

###中等 (Risco Moderado)
- `__pycache__/` - Pode revelar estrutura de código
- `.pytest_cache/` - Cache de testes
- `*.pyc`, `*.pyo` - Bytecode Python

### Baixo (Apenas Lixo)
- `.DS_Store`, `Thumbs.db` - Arquivos de sistema
- `*.swp`, `*.swo` - Swap de editores

## ✅ permits Arquivos que PODEM ser commitados

### Código Fonte
- `src/**/*.py` - Todo código fonte Python
- `tests/**/*.py` - Todos os testes

### Configuração (Templates apenas)
- `.env.example` - Template SEM segredos reais
- `pyproject.toml` - Dependências Poetry
- `config.yaml.example` - Config template
- `.gitignore` - Regras do Git

### Documentação
- `*.md` - Todos os arquivos Markdown
- `CLAUDE.md` - Documentação técnica

### Scripts e Docker
- `scripts/*.py`, `scripts/*.sql` - Scripts úteis
- `docker-compose.yml`, `docker/**` - Docker

## 🔐 Configuração de Secrets no GitHub

### Variáveis de Ambiente como Secrets

Configure em: **Settings → Secrets and variables → Actions**

| Secret | Como Gerar | Descrição |
|--------|------------|-----------|
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` | Chave JWT 256-bit |
| `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | Chave Fernet |
| `DATABASE_URL` | `postgresql://user:pass@host:port/db` | URL do PostgreSQL |
| `USE_SQLITE` | `true` ou `false` | Usar SQLite em dev |

### Nunca coloque em código

```python
# ❌ ERRADO - Segredo hardcoded
JWT_SECRET = "minha-chave-secreta-123"

# ✅ CERTO - Usa variável de ambiente
JWT_SECRET = os.environ.get("JWT_SECRET")
```

## 🚨 Se Acidentalmente Commitar Segredos

### Ação Imediata (Faça AGORA)

```bash
# 1. Remova o arquivo do histórico recente
git reset --soft HEAD~1
git reset HEAD arquivo_com_segrego.py

# 2. Apague o segredo vazado imediatamente!
# Se for JWT_SECRET ou ENCRYPTION_KEY, gere novos

# 3. Force push (se foi o último commit)
git push --force origin main
```

### Após Remover

1. **Invalide o segredo** - Gere novo JWT_SECRET e ENCRYPTION_KEY
2. **Atualize GitHub Secrets** - Settings → Secrets
3. **Monitore** - Verifique se não há uso indevido

## 🛡️ Branch Protection

Configure em: **Settings → Branches → Add rule**

Para a branch `main`:
- ✅ **Require a pull request before merging**
- ✅ **Require reviews** (1+ reviewers)
- ✅ **Require status checks to pass before merging**
- ✅ **Include administrators**

## 📝 Checklist de Pull Request

Antes de abrir PR:

- [ ] Nenhum `.env` ou segredo no código
- [ ] `.env.example` é apenas template (sem segredos reais)
- [ ] `.gitignore` inclui `.env`, `*.key`, `*.log`
- [ ] Tests passam: `pytest tests/`
- [ ] Syntax válida: `python scripts/verify_syntax.py`
- [ ] Mensagem de commit descritiva

---

**Última atualização:** 2026-07-04  
**Versão:** 3.0.1