# Olho de Deus v3 — notas para agentes

A documentação de uso está no `README.md`; este arquivo resume o que importa ao alterar o código.

## Mapa

- `main.py` — CLI (`--mode edge|api|all`, `--source`, `--max-frames`, carrega `.env`).
- `src/edge/` — `sources.py` (abre fontes), `pipeline.py` (frame → eventos → log forense),
  `analytics.py` (intrusão em zona, contagem/lotação, objeto abandonado), `processor.py`
  (detecção de rosto só para borrar), `streamer.py` (leitura em thread com reconexão).
- `src/hitl/dashboard_server.py` — app FastAPI. Rotas em `src/cloud/api/routes/`, auth em
  `src/cloud/api/middleware/auth.py` (OPERATOR_USERS + PBKDF2 + JWT), modelos em `src/cloud/models/`.
- `src/forensic/` — Merkle, logger forense e TSA (RFC 3161; não valida a assinatura).
- `src/privacy/` — borramento, Fernet com rotação, registro de base legal (LGPD).
- `src/tools/` — `bootstrap_env` (gera `.env`) e `sample_videos` (cenas sintéticas).
- `examples/` — 4 casos executáveis, testados em `tests/examples/`.

## Regras

- Não adicionar reconhecimento facial nem gravar embeddings: rostos só são detectados para borrar.
- Toda rota de dados exige `Depends(get_current_operator)`; decisões usam o operador do token.
- Nunca versionar `.env` nem senhas; `OPERATOR_USERS` guarda apenas hashes.
- Antes de concluir: `ruff check src tests main.py examples`, `ruff format --check ...`, mypy
  (lista no CI) e `USE_SQLITE=true python -m pytest -q --cov=src` (mínimo 70%).
