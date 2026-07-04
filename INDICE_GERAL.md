# 🗺️ ÍNDICE DO PROJETO - OLHO DE DEUS v3.0.1

**Data:** 2026-07-04  
**Versão:** 3.0.1

---

## 🚀 COMEÇE AQUI

| Para... | Vá para |
|---------|---------|
| **Instalar** | `GUIA_IMPLANTACAO_RAPIDA.md` |
| **Entender o sistema** | `README.md` |
| **Ver diagramas** | `/assets/` |
| **Desenvolver** | `CLAUDE.md` |
| **Configurar DB** | `scripts/setup_postgres.sql` |

---

## 📂 ESTRUTURA PRINCIPAL

### 📘 Documentação (Raiz)

| Arquivo | Descrição |
|---------|-----------|
| `README.md` | Visão geral + demos SVG |
| `CLAUDE.md` | Documentação técnica |
| `GUIA_IMPLANTACAO_RAPIDA.md` | Instalação passo a passo |
| `ESTRUTURA_PROJETO.md` | Estrutura de pastas |
| `ALTERACOES_RECENTES.md` | Histórico de mudanças |
| `CHECKLIST_VERIFICACAO_FINAL.md` | Checklist de produção |
| `AUDITORIA_SEGURANCA_VIES.md` | Relatório de auditoria |
| `RELATORIO_FINAL_IMPLANTACAO.md` | Guia completo |
| `ORGANIZACAO_CONCLUÍDA.md` | Resumo da organização |
| `ATUALIZACAO_SVGs_RESUMO.md` | 🆕 Resumo dos SVGs |
| `PROMPT_ENVIO_GITHUB.md` | Instruções de envio |
| `ENVIO_GITHUB_RAPIDO.md` | Guia rápido de commit |

### 🎨 Assets (Diagramas SVG)

| Arquivo | Descrição |
|---------|-----------|
| `assets/arquitetura-edge-cloud.svg` | Arquitetura completa |
| `assets/fluxo-edge-detection.svg` | Pipeline Edge AI |
| `assets/dashboard-hitl.svg` | Interface HITL |
| `assets/alerta-seguranca-v3.svg` | Fluxo de alertas |
| `assets/README.md` | Documentação dos SVGs |

### 🔧 Configuração

| Arquivo | Descrição |
|---------|-----------|
| `pyproject.toml` | Dependencies Poetry |
| `.env.example` | Template de ambiente |
| `.gitignore` | Git ignore rules |
| `setup_secure_install.py` | Instalação segura |

### 📂 Código Fonte (src/)

| Módulo | Descrição |
|--------|-----------|
| `src/edge/` | Edge AI (YOLOv8 + FaceNet) |
| `src/cloud/` | Cloud Backend (FastAPI + DB) |
| `src/forensic/` | Merkle Tree + TSA |
| `src/privacy/` | Dynamic Masking + Encryption |
| `src/fairness/` | Fairness Monitoring |
| `src/hitl/` | HITL Dashboard |

### 🧪 Testes

| Diretório | Descrição |
|-----------|-----------|
| `tests/edge/` | Testes de Edge AI |
| `tests/forensic/` | Testes de Forensic Logging |
| `tests/fairness/` | Testes de Fairness Metrics |

### 🛠️ Scripts

| Arquivo | Descrição |
|---------|-----------|
| `scripts/verify_syntax.py` | Verificador de sintaxe |
| `scripts/setup_postgres.sql` | Criação do banco |

---

## 🔍 ÍNDICE POR TÓPICO

### Arquitetura

1. `README.md` → Seção "Arquitetura Edge-to-Cloud"
2. `assets/arquitetura-edge-cloud.svg` (diagrama animado)
3. `CLAUDE.md` → Diagrama ASCII + componentes
4. `ESTRUTURA_PROJETO.md` → Estrutura completa

### Edge AI

1. `src/edge/processor.py` → YOLOv8-Face + FaceNet
2. `src/edge/streamer.py` → Captura RTSP
3. `src/edge/masker.py` → Dynamic Blur
4. `assets/fluxo-edge-detection.svg` (diagrama)

### HITL Dashboard

1. `src/hitl/dashboard_server.py` → API FastAPI
2. `src/hitl/operator_auth.py` → JWT Auth
3. `assets/dashboard-hitl.svg` (interface)
4. `GUIA_IMPLANTACAO_RAPIDA.md` → Como rodar

### Forensic Logging

1. `src/forensic/merkle_tree.py` → Árvore Merkle
2. `src/forensic/timestamp.py` → RFC 3161 TSA
3. `src/forensic/logger.py` → Forensic Logger
4. `AUDITORIA_SEGURANCA_VIES.md` → Validação

### Privacy by Design

1. `src/privacy/masker.py` → Dynamic Masking
2. `src/privacy/encryption.py` → Fernet
3. `src/privacy/conditional_unblur.py` → Two-Key System
4. `assets/arquitetura-edge-cloud.svg` → Fluxo LGPD

### Fairness

1. `src/fairness/metrics.py` → 4 métricas
2. `src/fairness/bias_detector.py` → Monitoramento
3. `AUDITORIA_SEGURANCA_VIES.md` → Relatório completo

### PostgreSQL

1. `scripts/setup_postgres.sql` → Cria banco
2. `src/cloud/database.py` → Configuração
3. `src/cloud/init_db.py` → Inicialização
4. `.env.example` → Template DATABASE_URL

### Segurança

1. `.github/SECURITY.md` → Políticas
2. `src/cloud/api/middleware/auth.py` → JWT
3. `src/cloud/api/middleware/rate_limiter.py` → Rate limit
4. `ENVIO_GITHUB_RAPIDO.md` → Checklist de commit

---

## 🎯 DIAGRAMAS SVG

| Diagrama | Use Para |
|----------|----------|
| `arquitetura-edge-cloud.svg` | Visão geral do sistema |
| `fluxo-edge-detection.svg` | Explicar Edge AI |
| `dashboard-hitl.svg` | Mostrar interface HITL |
| `alerta-seguranca-v3.svg` | Fluxo de alerta |

**Como incorporar:**
```markdown
![Arquitetura](assets/arquitetura-edge-cloud.svg)
```

---

## 📊 LEGADO v2.0.0

**Atenção:** Pasta `LEGADO_v2.0.0/` contém arquivos **ANTIGOS** - não usar em produção.

| Arquivo | Status |
|---------|--------|
| `LEGADO_v2.0.0/src/security_system.py` | ⚠️ Obsoleto |
| `LEGADO_v2.0.0/assets/*.svg` | ⚠️ Diagramas antigos |
| `LEGADO_v2.0.0/scripts/*.bat` | ⚠️ Scripts antigos |

---

## 🔗 LINKS RÁPIDOS

- **GitHub:** https://github.com/Lelolima/O-olho-de-DEUS
- **README.md:** Visão geral + demos
- **GUIA_IMPLANTACAO_RAPIDA.md:** Comece aqui para instalar
- **CLAUDE.md:** Referência técnica
- **assets/README.md:** Documentação dos SVGs

---

<div align="center">

**O-OLHO-DE-DEUS v3.0.1** • 2026-07-04

*Edge AI • Privacy by Design • Human-in-the-Loop • Forensic Logging*

</div>