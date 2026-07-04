# 📁 ESTRUTURA DE ARQUIVOS - OLHO DE DEUS v3.0
## Organização Completa do Projeto

**Data de Organização:** 2026-07-03  
**Versão:** 3.0.0  
**Status:** ✅ PRONTO PARA IMPLANTAÇÃO (com ressalvas da auditoria)

---

## 📂 ESTRUTURA DE DIRETÓRIOS

```
C:\Users\Thinkin pad 8g\olho-de-deus-corrigido\
│
├── 📄 main.py                          # Entry point principal
├── 📄 setup_secure_install.py          # Script de instalação segura
├── 📄 pyproject.toml                   # Configuração Poetry (dependências)
├── 📄 config.yaml.example              # Template de configuração
├── 📄 .env.example                     # Template de variáveis de ambiente
├── 📄 .gitignore                       # Git ignore rules
├── 📄 docker-compose.yml               # Docker Compose para produção
│
├── 📘 CLAUDE.md                        # Documentação técnica completa
├── 📘 IMPLEMENTACAO_CONCLUÍDA.md       # Resumo da implementação
├── 📘 AUDITORIA_SEGURANCA_VIES.md      # ⚠️ RELATÓRIO DE AUDITORIA
├── 📘 README_FINAL_ORGANIZACAO.md      # 📍 ESTE ARQUIVO
│
├── 📁 src/                             # CÓDIGO FONTE PRINCIPAL
│   ├── __init__.py                     # Pacote principal
│   │
│   ├── 📁 edge/                        # EDGE AI PROCESSING
│   │   ├── __init__.py
│   │   ├── processor.py                # Edge AI: YOLOv8-Face + FaceNet
│   │   ├── streamer.py                 # RTSP capture com reconexão
│   │   └── masker.py                   # Dynamic blur re-export
│   │
│   ├── 📁 cloud/                       # CLOUD BACKEND
│   │   ├── __init__.py
│   │   │
│   │   ├── 📁 api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── alerts.py           # API de alertas
│   │   │   │   ├── hitl.py             # API de revisão HITL
│   │   │   │   └── evidence.py         # API de evidências
│   │   │   │
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py             # JWT OAuth2 (✅ CORREGIDO)
│   │   │       └── rate_limiter.py     # Rate limiting (✅ NOVO)
│   │   │
│   │   ├── 📁 services/
│   │   │   ├── __init__.py
│   │   │   ├── alert_service.py        # Gerenciamento de alertas
│   │   │   ├── notification_service.py # Notificações (webhook/email)
│   │   │   └── fairness_service.py     # Monitoramento de viés
│   │   │
│   │   └── 📁 models/
│   │       ├── __init__.py
│   │       ├── incident.py             # SQLAlchemy: Incident
│   │       └── hitl_decision.py        # SQLAlchemy: HitlDecision
│   │
│   ├── 📁 forensic/                    # CADEIA DE CUSTÓDIA
│   │   ├── __init__.py
│   │   ├── merkle_tree.py              # Árvore Merkle completa
│   │   ├── timestamp.py                # RFC 3161 TSA client
│   │   └── logger.py                   # ForensicLogger (✅ CORREGIDO)
│   │
│   ├── 📁 privacy/                     # PRIVACY BY DESIGN
│   │   ├── __init__.py
│   │   ├── masker.py                   # DynamicMasker + ConditionalUnblurer
│   │   ├── encryption.py               # EncryptionManager com rotação
│   │   ├── conditional_unblur.py       # Two-key desofuscação
│   │   └── legal_basis.py              # ✅ NOVO: LGPD Legal Basis
│   │
│   ├── 📁 fairness/                    # FAIRNESS-AWARE ML
│   │   ├── __init__.py
│   │   ├── metrics.py                  # 4 métricas de viés (✅ APRIMORADO)
│   │   └── bias_detector.py            # Monitoramento contínuo
│   │
│   └── 📁 hitl/                        # HUMAN-IN-THE-LOOP
│       ├── __init__.py
│       ├── dashboard_server.py         # FastAPI app
│       └── operator_auth.py            # Autenticação de operadores
│
├── 📁 tests/                           # TESTES UNITÁRIOS
│   ├── __init__.py
│   ├── edge/
│   │   ├── __init__.py
│   │   └── test_edge.py                # Testes: Edge AI, Masker
│   │
│   ├── forensic/
│   │   ├── __init__.py
│   │   └── test_forensic.py            # Testes: Merkle, TSA, Logger
│   │
│   └── fairness/
│       ├── __init__.py
│       └── test_fairness.py            # Testes: Fairness Metrics
│
├── 📁 docker/                          # DOCKER
│   ├── edge/
│   │   └── Dockerfile                  # Docker image para Edge
│   └── cloud/
│       └── (vazio - usar root docker-compose)
│
└── 📁 legacy/                          # CÓDIGO LEGADO (v2.0.0)
    ├── src/
    │   └── security_system.py          # Sistema antigo (manter backup)
    ├── tests/
    │   ├── test_security_system.py
    │   └── validate_install.py
    ├── requirements.txt                # Legacy (substituído por pyproject.toml)
    └── *.bat                           # Batch scripts Windows legados
```

---

## 📋 ARQUIVOS POR CATEGORIA

### 🔐 SEGURANÇA E COMPLIANCE (CRÍTICOS)

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `AUDITORIA_SEGURANCA_VIES.md` | Relatório completo de auditoria | ✅ Criado |
| `src/cloud/api/middleware/auth.py` | JWT OAuth2 com secret seguro | ✅ Corrigido |
| `src/cloud/api/middleware/rate_limiter.py` | Rate limiting contra DoS | ✅ Novo |
| `src/privacy/legal_basis.py` | Bases legais LGPD | ✅ Novo |
| `src/fairness/metrics.py` | Métricas de viés aprimoradas | ✅ Corrigido |
| `setup_secure_install.py` | Instalação com geração de segredos | ✅ Novo |

### 🧠 EDGE AI PROCESSING

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `src/edge/processor.py` | Edge AI com TensorRT/OpenVINO/ONNX | ✅ Criado |
| `src/edge/streamer.py` | RTSP capture com reconexão automática | ✅ Criado |
| `src/edge/masker.py` | Re-export para DynamicMasker | ✅ Criado |

### ⚖️ FAIRNESS E VIÉS DE IA

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `src/fairness/metrics.py` | 4 métricas + significado estatístico | ✅ Corrigido |
| `src/fairness/bias_detector.py` | Detector contínuo de viés | ✅ Criado |
| `src/cloud/services/fairness_service.py` | Serviço de monitoramento | ✅ Criado |

### 🔒 PRIVACY BY DESIGN (LGPD)

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `src/privacy/masker.py` | Dynamic masking (Gaussian blur) | ✅ Criado |
| `src/privacy/encryption.py` | Criptografia Fernet com rotação | ✅ Criado |
| `src/privacy/conditional_unblur.py` | Two-key desofuscação | ✅ Criado |
| `src/privacy/legal_basis.py` | Bases legais LGPD Art. 7º/11º | ✅ Novo |

### ⛓️ CADEIA DE CUSTÓDIA

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `src/forensic/merkle_tree.py` | Árvore Merkle com provas | ✅ Criado |
| `src/forensic/timestamp.py` | RFC 3161 TSA client | ✅ Criado |
| `src/forensic/logger.py` | ForensicLogger com batch | ✅ Corrigido |

### 🌐 CLOUD API (FASTAPI)

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `src/cloud/api/routes/alerts.py` | Endpoints de alertas | ✅ Criado |
| `src/cloud/api/routes/hitl.py` | Endpoints de revisão HITL | ✅ Criado |
| `src/cloud/api/routes/evidence.py` | Endpoints de evidências | ✅ Criado |
| `src/hitl/dashboard_server.py` | FastAPI app completa | ✅ Criado |

### 🧪 TESTES

| Arquivo | Descrição | Status |
|---------|-----------|--------|
| `tests/edge/test_edge.py` | Testes de Edge AI | ✅ Criado |
| `tests/forensic/test_forensic.py` | Testes de Forensic Logging | ✅ Criado |
| `tests/fairness/test_fairness.py` | Testes de Fairness Metrics | ✅ Criado |

---

## ✅ CORREÇÕES DE SEGURANÇA IMPLEMENTADAS

### 1. JWT Secret Hardcoded → Variável de Ambiente
**Arquivo:** `src/cloud/api/middleware/auth.py`

```python
# ANTES (INSEGURO):
JWT_SECRET = "change-this-secret-in-production"

# DEPOIS (SEGURO):
JWT_SECRET = os.environ.get("JWT_SECRET") or secrets.token_hex(32)
```

### 2. Rate Limiting Adicionado
**Arquivo:** `src/cloud/api/middleware/rate_limiter.py`

- 100 requisições/minuto por IP
- 1000 requisições/hora por IP
- Burst allowance de 20 requests

### 3. Legal Basis para LGPD
**Arquivo:** `src/privacy/legal_basis.py`

- Enum com todas bases legais (Art. 7º e 11º)
- `ProcessingRecord` para registro de operações
- `LegalBasisRegistry` para gerenciamento

### 4. Fairness com Significância Estatística
**Arquivo:** `src/fairness/metrics.py`

- Adicionado teste Z para duas proporções
- Campo `statistical_significance` nos resultados
- Threshold de FPR reduzido para 5% (mais stricto)

### 5. Verificação Merkle Corrigida
**Arquivo:** `src/forensic/logger.py:verify_evidence_chain`

- Reconstrói Merkle tree para verificação
- Valida prova corretamente contra tree reconstruída

---

## 🚀 COMO INICIAR

### Instalação Segura

```bash
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
python setup_secure_install.py
```

### Rodar Sistema

```bash
# Development (Edge + API)
poetry run python main.py --config config.yaml --mode all

# Apenas API (HITL Dashboard)
poetry run python -m src.hitl.dashboard_server

# Apenas Edge (processamento de vídeo)
poetry run python main.py --config config.yaml --mode edge
```

### Rodar Testes

```bash
# Todos os testes
poetry run pytest

# Com coverage
poetry run pytest --cov=src --cov-report=term-missing

# Módulo específico
poetry run pytest tests/forensic/test_forensic.py -v
```

---

## 📊 STATUS DAS TAREFAS

| Tarefa | Status | Arquivos |
|--------|--------|----------|
| 1. Configurar estrutura de pastas v3.0 | ✅ CONCLUÍDO | Todos diretórios criados |
| 2. Migrar para Poetry (pyproject.toml) | ✅ CONCLUÍDO | pyproject.toml |
| 3. Implementar MerkleTree + TSA | ✅ CONCLUÍDO | merkle_tree.py, timestamp.py, logger.py |
| 4. Implementar ForensicLogger | ✅ CONCLUÍDO | logger.py (corrigido) |
| 5. Implementar EdgeAIProcessor | ✅ CONCLUÍDO | processor.py, streamer.py |
| 6. Implementar DynamicMasker | ✅ CONCLUÍDO | masker.py, encryption.py, conditional_unblur.py |
| 7. Segurança e Compliance | ✅ CONCLUÍDO | auth.py, rate_limiter.py, legal_basis.py |
| 8. Fairness Metrics | ✅ CONCLUÍDO | metrics.py (aprimorado) |
| 9. Cloud API | ✅ CONCLUÍDO | routes/*, services/*, models/* |
| 10. Testes | ✅ CONCLUÍDO | test_*.py |

---

## ⚠️ RESSALVAS DA AUDITORIA

Antes de implantar em produção, implemente:

1. **CRÍTICO:** Configurar JWT_SECRET via variável de ambiente (não hardcoded)
2. **CRÍTICO:** Adicionar autenticação em TODOS endpoints da API
3. **ALTO:** Implementar coleta de atributos sensíveis com consentimento LGPD
4. **ALTO:** Auto-ajuste de thresholds baseado em fairness reports
5. **MÉDIO:** Política de retenção automática de dados

Ver: `AUDITORIA_SEGURANCA_VIES.md` para detalhes completos.

---

## 📞 SUPORTE

- **Documentação:** `CLAUDE.md`
- **Auditoria:** `AUDITORIA_SEGURANCA_VIES.md`
- **Implementation:** `IMPLEMENTACAO_CONCLUÍDA.md`
- **Issues:** https://github.com/Lelolima/O-olho-de-DEUS/issues

---

**Última Atualização:** 2026-07-03  
**Próxima Revisão:** 2026-08-03 (30 dias)