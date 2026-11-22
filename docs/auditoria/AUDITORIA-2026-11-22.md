# Auditoria técnica — 2026-11-22

Ambiente: Windows 11, Python 3.11 (uv), SQLite (`USE_SQLITE=true`). Sem câmera, sem GPU, sem modelos ONNX, sem PostgreSQL.

## Estado anterior

| Item | Resultado |
|------|-----------|
| Finalidade | Vigilância com IA (v3): edge (RTSP, detecção facial, blur), API HITL FastAPI, cadeia de custódia (Merkle + TSA), privacidade, fairness |
| Instalação | `pyproject.toml` (Poetry); sem `requirements*.txt` |
| Testes | `pytest` **interrompido na coleta**: `src/forensic/__init__.py` importava `olho_de_deus.*` (pacote inexistente) e `cv2.CAP_MJPEG` (constante inexistente) |
| API | **Não importava**: `Integer` não importado em `hitl_decision.py`; `database.py` usava `Incident.__class__.metadata` (AttributeError); dois `declarative_base()` com FK entre eles |
| CI | Nenhum workflow |
| Vulnerabilidades | Faixas do Poetry presas em versões vulneráveis: `cryptography ^41`, `fastapi ^0.100`, `python-multipart ^0.0.6`, `pyjwt ^2.8`, `aiohttp ^3.8`, `python-jose ^3.3`, `requests ^2.31`, `pytest ^7.4`, `black ^23` |

## Segredos / credenciais expostas

| Arquivo | Linha (antes) | Tipo | Ação |
|---------|---------------|------|------|
| `src/cloud/api/middleware/auth.py` | 47–49 | 3 usuários (admin/operator1/supervisor) com **senhas em texto puro**, comparação sem tempo constante | removidos; usuários via `OPERATOR_USERS` com hash PBKDF2-SHA256 (600k iterações) e `hmac.compare_digest` |
| `ALTERACOES_RECENTES.md` | 229 | senha do admin em exemplo `curl` | substituída por `<SUA_SENHA>` |
| `GUIA_IMPLANTACAO_RAPIDA.md` | 100 | idem | idem |

Os valores **continuam no histórico do Git** (histórico não foi reescrito). **Ação do dono:** qualquer implantação que tenha usado essas senhas deve trocá-las e invalidar sessões; considere-as comprometidas.

Verificados e **não** sensíveis: `.env.example` (`JWT_SECRET`, `SMTP_PASS` são placeholders), `config.yaml.example` (`password` usa `${...}`), `src/cloud/database.py` (URL padrão `postgres:postgres@localhost`, credencial padrão de desenvolvimento — recomenda-se exigir `DATABASE_URL` em produção).

## Problemas e correções

| # | Sev. | Problema | Evidência | Correção |
|---|------|----------|-----------|----------|
| 1 | P0 | Senhas hardcoded | tabela acima; `tests/test_auth.py::test_no_hardcoded_users_without_env` | ver acima |
| 2 | P0 | `get_current_operator(token: str = oauth2_scheme)` sem `Depends`: o token nunca vinha do header `Authorization` | `test_protected_route_requires_bearer_token`, `test_login_then_token_accepted` | `Depends(oauth2_scheme)` |
| 3 | P1 | `require_role` era `async def` → `Depends(require_role(...))` recebia corrotina | leitura | `def` |
| 4 | P0 | API não importava (Integer, metadata, Bases separados) | `test_health` | import, Base único, `DatabaseBase = Base.metadata` |
| 5 | P0 | Testes não coletavam (`olho_de_deus`, `CAP_MJPEG`) | erro de coleta | `src.forensic`, `cv2.CAP_OPENCV_MJPEG` |
| 6 | P1 | `verify_evidence_chain` sempre lançava `ValueError` (`MerkleTree([])`) — cadeia de custódia nunca verificável | `test_evidence_chain_verification` | `verify_merkle_proof()` sem árvore + conferência da raiz do batch (`test_evidence_chain_rejects_tampered_root`) |
| 7 | P1 | Prova Merkle adulterada lançava exceção em vez de retornar `False` | `test_invalid_proof_tampered` | trata hex inválido |
| 8 | P2 | Teste de fairness com asserção impossível (`assertIsNone(x) or assertIn(...)`) | falha | teste reescrito para o comportamento documentado (mínimo `window_size // 10`) |
| 9 | P0 | Faixas de dependência vulneráveis | pip-audit | faixas atualizadas em `pyproject.toml`; `requirements-ci.txt` validado (`pip-audit`: sem vulnerabilidades) |
| 10 | P1 | Sem CI | — | workflow: ruff, compileall + import da API, pytest; `contents: read`; actions fixadas por SHA |
| 11 | P2 | README descrevia a v2 (`security_system.py`, `instalar.bat`) que só existe em `LEGADO_v2.0.0/`; benchmarks sem fonte | leitura | README da v3; benchmarks marcados como não verificados |

**Mudança de comportamento:** sem `OPERATOR_USERS`, nenhum login é aceito (antes havia contas padrão).

## Sobreposição com Project-Eyes-of-God-2.9

`Project-Eyes-of-God-2.9` é **cópia byte a byte** de `LEGADO_v2.0.0/` deste repositório: `src/security_system.py`, `tests/*`, `config.json`, `requirements.txt` e todos os scripts `.py`/`.bat` são idênticos (verificado com `cmp`). Nada foi unificado nem excluído; decisão de arquivamento é do dono.

## Testes executados (resultados reais)

```
antes:  pytest -> Interrupted: 2 errors during collection
        (após corrigir só a coleta: 3 failed, 20 passed)
depois: USE_SQLITE=true python -m pytest -q -p no:cacheprovider -o addopts=""  -> 33 passed
        ruff check --select E9,F63,F7,F82 src tests main.py                      -> All checks passed!
        pip-audit -r requirements-ci.txt                                         -> No known vulnerabilities found
        python main.py --help                                                    -> ok
        TestClient(app).get("/health")                                           -> 200 (SQLite)
```

## Não executado / riscos residuais

- Modo edge (RTSP/câmera, modelos YOLOv8-face/FaceNet ONNX): não executado — sem câmera e sem pesos.
- PostgreSQL/pgvector, Kafka, TSA externa (freetsa.org) e Docker: não executados.
- `poetry.lock` não existe e não foi gerado.
- Fairness: com um único grupo, o relatório indica `overall_passed: True` trivialmente — regra de negócio a revisar pelo dono.
- Reconhecimento facial em vigilância envolve dados biométricos (LGPD art. 11); conformidade depende da implantação.
