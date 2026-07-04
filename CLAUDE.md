# Olho de Deus v3.0 - Documentação Técnica

## Visão Geral

Sistema de vigilância com IA para detecção facial e comportamental, com:
- **Edge Computing**: Processamento na borda (RTSP → metadados)
- **Privacy by Design**: Dynamic masking de rostos (blur)
- **Cadeia de Custódia**: Merkle Tree + Timestamp Authority
- **Human-in-the-Loop**: Dashboard para triagem humana
- **Fairness Monitoring**: Detecção de viés algorítmico

## Arquitetura

```
[Câmeras RTSP] → [Edge AI] → [Metadados JSON] → [Cloud API] → [HITL Dashboard]
                     ↓              ↓                  ↓
               [Blur Rostos]  [Hash SHA-256]    [PostgreSQL + pgvector]
                                      ↓
                              [Merkle Tree → TSA]
```

## Estrutura de Pastas

```
olho-de-deus-corrigido/
├── src/
│   ├── edge/                    # Edge AI Processing
│   │   ├── processor.py         # YOLOv8-Face + FaceNet
│   │   ├── streamer.py          # RTSP capture com reconexão
│   │   └── masker.py            # Dynamic blur
│   │
│   ├── cloud/                   # Cloud Backend
│   │   ├── api/
│   │   │   ├── routes/          # Endpoints FastAPI
│   │   │   └── middleware/      # Auth JWT
│   │   ├── services/            # Business logic
│   │   └── models/              # SQLAlchemy models
│   │
│   ├── forensic/                # Cadeia de Custódia
│   │   ├── merkle_tree.py       # Árvore Merkle
│   │   ├── timestamp.py         # RFC 3161 TSA
│   │   └── logger.py            # Forensic logging
│   │
│   ├── privacy/                 # Privacy by Design
│   │   ├── masker.py            # DynamicMasker
│   │   ├── encryption.py        # Fernet encryption
│   │   └── conditional_unblur.py# Two-key unblur
│   │
│   ├── fairness/                # Fairness-Aware ML
│   │   ├── metrics.py           # Demographic parity, etc.
│   │   └── bias_detector.py     # Continuous monitoring
│   │
│   └── hitl/                    # Human-in-the-Loop
│       ├── dashboard_server.py  # FastAPI app
│       └── operator_auth.py     # JWT auth
│
├── tests/
│   ├── edge/
│   ├── forensic/
│   └── fairness/
│
├── main.py                      # Entry point
├── pyproject.toml               # Poetry dependencies
├── config.yaml.example          # Config template
└── .env.example                 # Environment template
```

## Instalação

```bash
# Instalar Poetry (se não tiver)
pip install poetry

# Instalar dependências
poetry install

# Copiar configs
cp config.yaml.example config.yaml
cp .env.example .env

# Rodar testes
poetry run pytest

# Rodar sistema
poetry run python main.py --config config.yaml --mode all
```

## Componentes Principais

### Edge AI Processor (`src/edge/processor.py`)

```python
from src.edge.processor import EdgeAIProcessor

processor = EdgeAIProcessor(
    face_model_path="models/yolov8-face.onnx",
    embedding_model_path="models/facenet.onnx",
    backend="onnx",  # haar, onnx, tensorrt, openvino
    device="CPU"
)

faces, masked_frame = processor.process_frame(frame)
```

### Forensic Logger (`src/forensic/logger.py`)

```python
from src.forensic.logger import ForensicLogger

logger = ForensicLogger(
    log_dir="./forensic_logs",
    tsa_enabled=True,
    batch_size=100
)

evidence = {
    "id": "evt_001",
    "camera_id": "CAM-001",
    "timestamp": "2026-07-03T14:32:18Z",
    "alarm_score": 0.97
}

logged = logger.log_evidence(evidence)
```

### Fairness Metrics (`src/fairness/metrics.py`)

```python
from src.fairness.metrics import FairnessMetrics

metrics = FairnessMetrics()

report = metrics.generate_fairness_report(
    predictions=y_pred,
    ground_truth=y_true,
    sensitive_attrs=sensitive_attr
)

print(f"Fairness passed: {report['overall_passed']}")
```

### Cloud API (`src/hitl/dashboard_server.py`)

```bash
# Rodar API
poetry run python -m src.hitl.dashboard_server

# Acessar docs
http://localhost:8000/docs
```

Endpoints principais:
- `POST /api/v1/alerts/` - Criar alerta
- `POST /api/v1/alerts/{id}/review` - Revisão HITL
- `POST /api/v1/evidence/upload` - Upload de evidência
- `POST /api/v1/auth/token` - Login operador

## API de Produção

### PostgreSQL

```bash
# Instalar
docker run -d -e POSTGRES_PASSWORD=secret -p 5432:5432 postgres:15

# Migrar
poetry run alembic upgrade head
```

### Docker

```bash
# Build
docker-compose build

# Rodar
docker-compose up -d
```

## Testes

```bash
# Todos testes
poetry run pytest

# Com coverage
poetry run pytest --cov=src --cov-report=html

# Específico módulo
poetry run pytest tests/forensic/test_forensic.py
```

## LGPD e Compliance

### Princípios Implementados

1. **Minimização**: Apenas metadados saem da borda
2. **Anonimização**: Dynamic masking de rostos
3. **Audit Trail**: Forensic log com Merkle Tree
4. **HITL**: Revisão humana antes de notificar autoridades
5. **Fairness**: Monitoramento contínuo de viés

### Relatório de Impacto (RIPD)

O sistema implementa:
- Criptografia Fernet para dados sensíveis
- Timestamp RFC 3161 para prova de anterioridade
- Logs imutáveis de acesso a evidências
- Thresholds de confiança com histerese

## Troubleshooting

### Edge AI lento
- Verificar se GPU está disponível (`nvidia-smi`)
- Usar backend `onnx` com `CUDAExecutionProvider`
- Reduzir resolução de entrada

### TSA falhando
- Verificar conectividade com `curl https://freetsa.org/tsr`
- Usar TSA alternativa em `config.yaml`

### Viés detectado
- Revisar dataset de treinamento
- Ajustar thresholds em `config.yaml`
- Implementar revisão humana adicional

## Contribuição

1. Fork o repositório
2. Crie branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push (`git push origin feature/nova-funcionalidade`)
5. Open Pull Request

## Licença

MIT License - ver LICENSE