# 📁 GUIA DE ORGANIZAÇÃO - Separar LEGADO v2.0.0 do NOVO v3.0.1

## ⚠️ ATENÇÃO: Arquivos Misturados

O diretório atual contém arquivos do projeto **LEGADO v2.0.0** misturados com o projeto **NOVO v3.0.1**.

### Arquivos LEGADOS (devem ser movidos)

| Arquivo | Localização Atual | Destino |
|---------|-------------------|---------|
| `security_system.py` | `src/security_system.py` | `LEGADO_v2.0.0/src/` |
| `requirements.txt` | Raiz | `LEGADO_v2.0.0/` |
| `config.json` | Raiz | `LEGADO_v2.0.0/` |
| `test_security_system.py` | `tests/` | `LEGADO_v2.0.0/tests/` |
| `validate_install.py` | `tests/` | `LEGADO_v2.0.0/tests/` |
| `*.bat` (6 arquivos) | Raiz | `LEGADO_v2.0.0/scripts/` |
| `deploy.py` | Raiz | `LEGADO_v2.0.0/scripts/` |
| `deploy-gitpython.py` | Raiz | `LEGADO_v2.0.0/scripts/` |
| `fix-and-push.py` | Raiz | `LEGADO_v2.0.0/scripts/` |
| `enviar-github.py` | Raiz | `LEGADO_v2.0.0/scripts/` |
| `check-repo.py` | Raiz | `LEGADO_v2.0.0/scripts/` |
| `upload-github-api.py` | Raiz | `LEGADO_v2.0.0/scripts/` |
| `assets/` (pasta) | Raiz | `LEGADO_v2.0.0/` |

### Arquivos NOVOS (permanecem na raiz)

| Arquivo/Pasta | Descrição |
|---------------|-----------|
| `src/edge/` | Edge AI Processing |
| `src/cloud/` | Cloud Backend |
| `src/forensic/` | Forensic Logging |
| `src/privacy/` | Privacy by Design |
| `src/fairness/` | Fairness ML |
| `src/hitl/` | HITL Dashboard |
| `main.py` | Entry point v3.0.1 |
| `pyproject.toml` | Poetry config |
| `setup_secure_install.py` | Instalação segura |
| `.env.example` | Template de ambiente |
| `CLAUDE.md` | Documentação técnica |
| `CHECKLIST_VERIFICACAO_FINAL.md` | Checklist |
| `ALTERACOES_RECENTES.md` | Histórico de mudanças |
| `GUIA_IMPLANTACAO_RAPIDA.md` | Guia rápido |

---

## 🚀 COMO ORGANIZAR (Manual)

### Opção 1: Executar Script Automático

```powershell
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
.\ORGANIZAR_ARQUIVOS.ps1
```

### Opção 2: Mover Manualmente (PowerShell)

```powershell
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"

# Criar pastas LEGADO
New-Item -ItemType Directory -Path "LEGADO_v2.0.0\src" -Force
New-Item -ItemType Directory -Path "LEGADO_v2.0.0\scripts" -Force
New-Item -ItemType Directory -Path "LEGADO_v2.0.0\assets" -Force
New-Item -ItemType Directory -Path "LEGADO_v2.0.0\tests" -Force

# Mover arquivos
Move-Item src\security_system.py LEGADO_v2.0.0\src\
Move-Item requirements.txt LEGADO_v2.0.0\
Move-Item config.json LEGADO_v2.0.0\
Move-Item tests\test_security_system.py LEGADO_v2.0.0\tests\
Move-Item tests\validate_install.py LEGADO_v2.0.0\tests\
Move-Item *.bat LEGADO_v2.0.0\scripts\
Move-Item deploy.py LEGADO_v2.0.0\scripts\
Move-Item deploy-gitpython.py LEGADO_v2.0.0\scripts\
Move-Item fix-and-push.py LEGADO_v2.0.0\scripts\
Move-Item enviar-github.py LEGADO_v2.0.0\scripts\
Move-Item check-repo.py LEGADO_v2.0.0\scripts\
Move-Item upload-github-api.py LEGADO_v2.0.0\scripts\
Move-Item assets LEGADO_v2.0.0\
```

---

## 📊 ESTRUTURA FINAL

```
olho-de-deus-corrigido/
├── LEGADO_v2.0.0/           ← ARQUIVOS ANTIGOS (não usar)
│   ├── src/
│   │   └── security_system.py
│   ├── scripts/
│   │   ├── *.bat
│   │   └── *.py (scripts antigos)
│   ├── tests/
│   │   ├── test_security_system.py
│   │   └── validate_install.py
│   ├── assets/
│   └── MANIFESTO_LEGADO.md
│
├── src/                     ← PROJETO NOVO v3.0.1
│   ├── edge/
│   ├── cloud/
│   ├── forensic/
│   ├── privacy/
│   ├── fairness/
│   └── hitl/
├── tests/                   ← Testes novos v3.0.1
├── main.py                  ← Entry point
├── pyproject.toml
├── setup_secure_install.py
├── .env.example
└── CLAUDE.md                ← Documentação
```

---

## ✅ VERIFICAÇÃO PÓS-ORGANIZAÇÃO

Após organizar, verifique:

1. **Raiz NÃO deve conter:**
   - [ ] `security_system.py`
   - [ ] `requirements.txt`
   - [ ] `config.json`
   - [ ] Arquivos `.bat`
   - [ ] `assets/` pasta

2. **Raiz DEVE conter:**
   - [ ] `src/edge/`
   - [ ] `src/cloud/`
   - [ ] `src/forensic/`
   - [ ] `main.py`
   - [ ] `pyproject.toml`

3. **LEGADO_v2.0.0 DEVE conter:**
   - [ ] `src/security_system.py`
   - [ ] `requirements.txt`
   - [ ] `scripts/*.bat`
   - [ ] `assets/`

---

## 🔄 RENOMEAR DIRETÓRIOS (Opcional)

Para clareza total:

```powershell
# Renomear projeto novo
cd "C:\Users\Thinkin pad 8g"
Rename-Item "olho-de-deus-corrigido" "Olho-de-Deus-CORRIGIDO-3.0.1"

# Renomear projeto legado
Rename-Item "Olho-de-Deus-CORRIGIDO-3.0.1\LEGADO_v2.0.0" "Olho-de-Deus-LEGADO-2.0.0"
```

---

**Criado em:** 2026-07-04  
**Versão:** 3.0.1  
**Status:** Aguardando execução da organização