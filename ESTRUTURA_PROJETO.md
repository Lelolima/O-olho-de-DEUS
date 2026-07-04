# 📁 ESTRUTURA DO PROJETO - OLHO DE DEUS v3.0.1

**Data:** 2026-07-04  
**Versão:** 3.0.1

---

## 🗂️ ESTRUTURA DE ARQUIVOS

```
olho-de-deus-corrigido/
│
├── 📘 DOCUMENTAÇÃO
│   ├── CLAUDE.md                      # Documentação técnica principal
│   ├── README.md                      # README do projeto
│   ├── IMPLEMENTACAO_CONCLUÍDA.md     # Resumo da implementação
│   ├── AUDITORIA_SEGURANCA_VIES.md    # Relatório de auditoria
│   ├── CHECKLIST_VERIFICACAO_FINAL.md # Checklist de verificação
│   ├── RELATORIO_FINAL_IMPLANTACAO.md # Guia de implantação
│   ├── ALTERACOES_RECENTES.md         # Histórico de mudanças (2026-07-04)
│   ├── GUIA_IMPLANTACAO_RAPIDA.md     # Guia rápido de instalação
│   └── ESTRUTURA_PROJETO.md           # ← ESTE ARQUIVO
│
├── 🔧 CONFIGURAÇÃO
│   ├── pyproject.toml                 # Dependencies Poetry
│   ├── .env.example                   # Template de variáveis de ambiente
│   ├── .gitignore                     # Git ignore rules
│   └── setup_secure_install.py        # Script de instalação segura
│
├── 📂 SRC/ (CÓDIGO FONTE v3.0.1)
│   ├── edge/                          # Edge AI Processing
│   │   ├── processor.py               # YOLOv8-Face + FaceNet
│   │   ├── streamer.py                # RTSP capture
│   │   └── masker.py                  # Dynamic blur
│   │
│   ├── cloud/                         # Cloud Backend
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── alerts.py          # ✅ Atualizado 2026-07-04
│   │   │   │   ├── evidence.py        # ✅ Atualizado 2026-07-04
│   │   │   │   └── hitl.py
│   │   │   └── middleware/
│   │   │       ├── auth.py            # JWT OAuth2
│   │   │       └── rate_limiter.py    # Rate limiting
│   │   ├── services/
│   │   ├── models/
│   │   ├── database.py                # ✅ NOVO: PostgreSQL config
│   │   └── init_db.py                 # ✅ NOVO: DB initialization
│   │
│   ├── forensic/                      # Cadeia de Custódia
│   │   ├── merkle_tree.py             # Árvore Merkle
│   │   ├── timestamp.py               # RFC 3161 TSA
│   │   └── logger.py                  # Forensic logging
│   │
│   ├── privacy/                       # Privacy by Design
│   │   ├── masker.py                  # Dynamic masking
│   │   ├── encryption.py              # Fernet encryption
│   │   ├── conditional_unblur.py      # Two-key unblur
│   │   └── legal_basis.py             # LGPD compliance
│   │
│   ├── fairness/                      # Fairness-Aware ML
│   │   ├── metrics.py                 # 4 fairness metrics
│   │   └── bias_detector.py           # Continuous monitoring
│   │
│   └── hitl/                          # Human-in-the-Loop
│       ├── dashboard_server.py        # ✅ Atualizado: Health check DB
│       └── operator_auth.py           # JWT authentication
│
├── 🧪 TESTES
│   ├── edge/
│   │   ├── test_edge.py
│   │   └── __init__.py
│   ├── forensic/
│   │   ├── test_forensic.py
│   │   └── __init__.py
│   ├── fairness/
│   │   ├── test_fairness.py
│   │   └── __init__.py
│   └── __init__.py
│
├── 🛠️ SCRIPTS (Utilitários)
│   ├── verify_syntax.py               # Verificação de sintaxe Python
│   ├── setup_postgres.sql             # Script de criação do banco
│   └── organizar.bat                  # Script de organização LEGADO
│
├── 📝 ENTRY POINTS
│   ├── main.py                        # Entry point principal
│   └── -m src.hitl.dashboard_server   # API server
│
└── 🗄️ LEGADO_v2.0.0/                  # ARQUIVOS ANTIGOS (não usar)
    ├── src/security_system.py
    ├── scripts/ (antigos .bat e .py)
    ├── tests/
    ├── assets/
    └── MANIFESTO_LEGADO.md
```

---

## ✅ ARQUIVOS DE CORREÇÕES RECENTES (2026-07-04)

### Implementados na v3.0.1

| Arquivo | Localização | Descrição |
|---------|-------------|-----------|
| `database.py` | `src/cloud/` | Configuração PostgreSQL + Repositórios |
| `init_db.py` | `src/cloud/` | Inicialização de tabelas |
| `alerts.py` | `src/cloud/api/routes/` | Atualizado: Autenticação + DB |
| `evidence.py` | `src/cloud/api/routes/` | Atualizado: Autenticação + DB |
| `dashboard_server.py` | `src/hitl/` | Atualizado: Health check com DB |
| `.env.example` | Raiz | Atualizado: Template completo |
| `setup_postgres.sql` | `scripts/` | Script para criar banco PostgreSQL |
| `verify_syntax.py` | `scripts/` | Verificador de sintaxe |

### Documentação Atualizada

| Arquivo | Descrição |
|---------|-----------|
| `ALTERACOES_RECENTES.md` | Histórico das mudanças v3.0.1 |
| `CHECKLIST_VERIFICACAO_FINAL.md` | Checklist atualizado (v3.0.1) |
| `GUIA_IMPLANTACAO_RAPIDA.md` | Guia rápido de instalação |
| `ESTRUTURA_PROJETO.md` | ← Este arquivo |

---

## 🔍 LOCALIZAÇÃO RÁPIDA

### Para Desenvolvimento

| Precisa de... | Arquivo |
|---------------|---------|
| Rodar API | `python -m src.hitl.dashboard_server` |
| Rodar sistema | `python main.py --config config.yaml --mode all` |
| Inicializar DB | `python -m src.cloud.init_db` |
| Testes | `pytest tests/` |
| Configurar ambiente | Copiar `.env.example` para `.env` |

### Para Produção

| Precisa de... | Arquivo |
|---------------|---------|
| Configurar PostgreSQL | `scripts/setup_postgres.sql` |
| Health check | `GET http://localhost:8000/health` |
| Autenticação | `POST http://localhost:8000/api/v1/auth/token` |
| Criptografia | `.env` → `ENCRYPTION_KEY`, `JWT_SECRET` |

---

## ⚠️ IMPORTANTE

- **LEGADO_v2.0.0/** contém arquivos do projeto v2.0.0 - **NÃO USAR**
- Todos os arquivos de código **ativo** estão em `src/`
- Scripts utilitários estão em `scripts/`
- Documentação está na **raiz**

---

**Última Atualização:** 2026-07-04  
**Versão:** 3.0.1  
**Status:** ✅ Organizado
