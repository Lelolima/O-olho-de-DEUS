# 04 — Fluxo completo com revisão humana (HITL) e cadeia de custódia

**Problema:** um alerta de câmera só deve virar ação depois que uma pessoa autorizada o
revisar. Tudo precisa ficar auditável: quem decidiu, quando, e a prova de que a imagem não
foi alterada.

**O que o exemplo faz, de verdade:**

1. Roda a detecção de intrusão sobre o vídeo. O frame salvo passa pelo borrador de rostos (Haar).
2. Sobe a **API real** em processo (FastAPI `TestClient`, sem abrir porta) com um operador de
   demonstração. A senha é aleatória, gerada em memória, guardada só como hash PBKDF2 e nunca impressa.
3. O operador faz login (JWT), cria o alerta, envia o frame como evidência, revisa e **escala**.
4. A API verifica a integridade da evidência (SHA-256) e o log forense da borda confere a prova Merkle.

## Como rodar

```bash
python examples/04_fluxo_hitl_completo/run.py
```

Sem `DATABASE_URL`, o exemplo usa SQLite local (`olho_de_deus.db` no diretório atual).

## Saída esperada (valores reais)

```json
{"status_inicial_alerta": "pending", "decisao_operador": "escalate",
 "operador_registrado": "operador.demo", "status_final_alerta": "escalated",
 "evidencia_integra": true, "cadeia_merkle_valida": true}
```

`operador_registrado` vem do token JWT, não do corpo da requisição: um operador não consegue
registrar uma decisão em nome de outro.
