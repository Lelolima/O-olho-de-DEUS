# 01 — Intrusão em área restrita fora do horário

**Problema:** o pátio dos fundos de uma empresa não pode ter movimento entre 19h e 7h.
Durante o expediente, circular por ali é normal e não deve gerar alerta.

**Como funciona:** `ZoneIntrusionDetector` aplica subtração de fundo (MOG2) e alerta quando
o centro de um objeto em movimento entra no polígono da zona, apenas dentro da agenda
`[("19:00", "07:00")]`. Um intervalo mínimo (`cooldown_seconds`) evita uma enxurrada de alertas.
Cada alerta vira evidência no log forense encadeado (Merkle).

## Como rodar

```bash
python examples/01_intrusao_fora_do_horario/run.py                                  # 22:30 → alerta
python examples/01_intrusao_fora_do_horario/run.py --inicio 2026-11-22T10:00:00     # 10:00 → sem alerta
python examples/01_intrusao_fora_do_horario/run.py --video minha_camera.mp4 --inicio 2026-11-22T23:00:00
```

Sem `--video`, o exemplo gera uma cena sintética: uma pessoa entra pela direita e caminha
até a metade esquerda (zona restrita). Com `--video`, ele usa o seu arquivo.

## Saída esperada (cena sintética, valores reais de execução)

| `--inicio` | `zona_ativa_no_horario` | `events_by_type` |
|---|---|---|
| `2026-11-22T22:30:00` | `true` | `{"zone_intrusion": 1}` (frame 42) |
| `2026-11-22T10:00:00` | `false` | `{}` |

Arquivos em `--saida` (padrão `saida_exemplo/`): `forense/` (evidências + batch Merkle) e
`snapshots/00042_zone_intrusion.jpg` com a caixa do objeto.
