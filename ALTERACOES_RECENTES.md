# 📝 ALTERAÇÕES RECENTES - OLHO DE DEUS v3.0.1

**Data:** 2026-07-04  
**Versão:** 3.0.1 (pós-auditoria + diagramas SVG)

---

## ✅ CORREÇÕES IMPLEMENTADAS

### 1. Autenticação em Endpoints Críticos ✅

**Problema:** Endpoints `/api/v1/alerts/` e `/api/v1/evidence/upload` estavam públicos.

**Solução:** Adicionado `Depends(get_current_operator)` em todos os endpoints críticos.

**Arquivos alterados:**
- `src/cloud/api/routes/alerts.py` - Autenticação em POST, GET, PUT
- `src/cloud/api/routes/evidence.py` - Autenticação em upload e verify

### 2. Persistência com PostgreSQL ✅

**Problema:** Alertas e evidências eram armazenados apenas em memória (`_alerts_store`).

**Solução:** Implementado repositórios SQLAlchemy com fallback para memória.

**Novos arquivos:**
- `src/cloud/database.py` - Configuração de DB e repositórios
- `src/cloud/init_db.py` - Script de inicialização do banco
- `setup_postgres.sql` - Script SQL para criar banco e usuário

**Arquivos alterados:**
- `src/cloud/api/routes/alerts.py` - Integração com IncidentRepository
- `src/cloud/api/routes/evidence.py` - Integração com EvidenceRepository
- `src/hitl/dashboard_server.py` - Inicialização do DB no startup
- `.env.example` - Adicionado template para DATABASE_URL

### 3. Health Check Aprimorado ✅

**Problema:** Health check não mostrava status do banco de dados.

**Solução:** Endpoint `/health` agora retorna:
- Status do banco de dados (connected/disconnected)
- Status do forensic logger
- Status geral (healthy/degraded)

---

## 📁 ESTRUTURA ATUALIZADA

```
olho-de-deus-corrigido/
├── src/
│   ├── cloud/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── alerts.py         ✅ Com PostgreSQL + fallback
│   │   │   │   ├── evidence.py       ✅ Com PostgreSQL + fallback
│   │   │   │   └── hitl.py
│   │   │   └── middleware/
│   │   │       ├── auth.py           ✅ JWT seguro
│   │   │       └── rate_limiter.py   ✅ Rate limiting
│   │   ├── models/
│   │   │   ├── incident.py           ✅ SQLAlchemy models
│   │   │   └── hitl_decision.py
│   │   ├── database.py               ✅ NOVO: Configuração DB
│   │   └── init_db.py                ✅ NOVO: Inicialização
│   ├── hitl/
│   │   └── dashboard_server.py       ✅ Com health check DB
│   ├── forensic/
│   │   ├── merkle_tree.py
│   │   ├── timestamp.py
│   │   └── logger.py
│   ├── privacy/
│   │   ├── masker.py
│   │   ├── encryption.py
│   │   └── conditional_unblur.py
│   ├── fairness/
│   │   ├── metrics.py
│   │   └── bias_detector.py
│   └── edge/
│       ├── processor.py
│       └── streamer.py
├── .env.example                      ✅ Atualizado
├── setup_postgres.sql                ✅ NOVO: Script para criar DB
├── pyproject.toml
└── CLAUDE.md
```

---

## 🎨 DIAGRAMAS SVG ATUALIZADOS (v3.0.1)

**Data:** 2026-07-04

**Novos arquivos:**
- `assets/arquitetura-edge-cloud.svg` - Arquitetura Edge-to-Cloud completa
- `assets/fluxo-edge-detection.svg` - Pipeline de detecção Edge AI
- `assets/dashboard-hitl.svg` - Interface do HITL Dashboard
- `assets/alerta-seguranca-v3.svg` - Fluxo de alerta de segurança
- `assets/README.md` - Documentação dos diagramas

**O que cada diagrama mostra:**

| Diagrama | Componentes Principais | Animações |
|----------|------------------------|-----------|
| **Arquitetura** | Edge Layer, Cloud Layer, Merkle Tree, TSA, HITL, Fairness | Pulse, data flow, glow |
| **Fluxo Edge** | RTSP → YOLOv8 → FaceNet → Masking → JSON | Scan, embed pulse, threshold |
| **Dashboard** | WebSocket, Fila de Alertas, HITL, Fairness | Blink, slide, spinner |
| **Alerta** | Detecção → Threshold → HITL → Notificação | Siren, shake, pulse |

**Diferenças vs v2.0 (LEGADO):**

| Aspecto | v2.0 | v3.0.1 |
|---------|------|---------|
| Processamento | Centralizado (OpenCV + Haar) | Edge AI (YOLOv8 + FaceNet) |
| Dados na Cloud | Frames brutos | Apenas metadados JSON |
| Privacidade | Sem blur | Dynamic Masking na borda |
| Cadeia Custódia | Hash simples | Merkle Tree + TSA |
| Notificação | Automática | HITL obrigatório |

**Como usar:**
```markdown
![Arquitetura](assets/arquitetura-edge-cloud.svg)
![Fluxo Edge](assets/fluxo-edge-detection.svg)
![Dashboard](assets/dashboard-hitl.svg)
![Alerta](assets/alerta-seguranca-v3.svg)
```

---

## 🚀 COMO CONFIGURAR POSTGRESQL

### Opção 1: Script Automático (Windows)

```bash
# Se tiver PostgreSQL instalado
psql -U postgres -f setup_postgres.sql
```

### Opção 2: Manual

```sql
-- Crie o banco
CREATE DATABASE olho_de_deus;

-- Crie o usuário
CREATE USER olho_de_deus_user WITH PASSWORD 'sua_senha_forte';

-- Conceda privilégios
GRANT ALL PRIVILEGES ON DATABASE olho_de_deus TO olho_de_deus_user;
```

### Opção 3: SQLite (Desenvolvimento)

No `.env`:
```
USE_SQLITE=true
```

Isso usa `olho_de_deus.db` localmente sem precisar de PostgreSQL.

---

## 🔧 COMANDOS ÚTEIS

### Inicializar Banco de Dados

```bash
# Cria tabelas
python -m src.cloud.init_db
```

### Rodar API

```bash
# Com PostgreSQL
poetry run python -m src.hitl.dashboard_server

# Com SQLite
USE_SQLITE=true poetry run python -m src.hitl.dashboard_server
```

### Verificar Saúde

```bash
curl http://localhost:8000/health
```

### Rodar Testes

```bash
poetry run pytest tests/forensic/test_forensic.py -v
```

---

## ⚠️ NOTAS IMPORTANTES

### Fallback para Memória

Se o banco de dados não estiver disponível, o sistema automaticamente:
1. Tenta conectar ao PostgreSQL
2. Se falhar, usa SQLite (se `USE_SQLITE=true`)
3. Se ambos falharem, usa armazenamento em memória

**Atenção:** Dados em memória são perdidos ao reiniciar a API.

### Produção

Para produção, **sempre** use PostgreSQL com:
- `JWT_SECRET` definido no `.env`
- `ENCRYPTION_KEY` gerada corretamente
- `DATABASE_URL` com credenciais seguras

---

## 📊 TESTES DE VERIFICAÇÃO

### 1. Verificar Autenticação

```bash
# Sem token (deve falhar)
curl -X POST http://localhost:8000/api/v1/alerts/ \
  -H "Content-Type: application/json" \
  -d '{"camera_id":"CAM-001","alarm_score":0.9}'

# Com token (deve funcionar)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin" -d "password=admin123" | jq -r .access_token)

curl -X POST http://localhost:8000/api/v1/alerts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"camera_id":"CAM-001","alarm_score":0.9}'
```

### 2. Verificar Banco de Dados

```bash
# Health check
curl http://localhost:8000/health | jq
```

Saída esperada:
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "database": "connected",
  "forensic_logger": "active"
}
```

---

## 📝 PRÓXIMOS PASSOS

### Pendentes para Produção

1. [ ] Configurar backup automático do PostgreSQL
2. [ ] Implementar migrations com Alembic
3. [ ] Adicionar pooling de conexões (PgBouncer)
4. [ ] Configurar monitoramento (Prometheus + Grafana)
5. [ ] Implementar rate limiting por IP/user
6. [ ] Adicionar endpoint para deleção (direito ao esquecimento LGPD)
7. [ ] Dashboard de métricas de fairness em tempo real

---

**Implementado por:** Claude Opus 4.8  
**Revisão:** 2026-07-04  
**Próxima revisão:** 2026-07-11 (7 dias)