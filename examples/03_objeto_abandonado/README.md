# 03 — Objeto abandonado

**Problema:** no saguão de um prédio, uma mala deixada sozinha por mais de alguns minutos
deve ser checada pela equipe.

**Como funciona:** `AbandonedObjectDetector` aprende o fundo nos primeiros frames. Depois,
marca regiões que **diferem do fundo e não estão se movendo**. Se uma região fica assim por
`--segundos`, gera `abandoned_object` (uma vez por local). O fundo se adapta lentamente à
iluminação apenas onde não há objeto.

**Limitação:** uma pessoa parada pelo mesmo tempo também dispara o alerta. Por isso ele vai
para revisão humana (HITL) e nunca para uma ação automática.

## Como rodar

```bash
python examples/03_objeto_abandonado/run.py                 # limiar de 5 s (cena curta)
python examples/03_objeto_abandonado/run.py --segundos 60
python examples/03_objeto_abandonado/run.py --video saguao.mp4 --segundos 120
```

## Saída esperada (cena sintética, valores reais)

A pessoa entra com a mala, deixa-a no chão no frame 40 e sai. O alerta sai no frame 94:
o objeto fica 5 s parado depois que a pessoa se afasta.

```json
{"events_by_type": {"abandoned_object": 1},
 "alertas": [{"type": "abandoned_object", "frame_index": 94, "details": {"box": [151, 178, 26, 20]}}]}
```

A caixa coincide com a mala desenhada em `(150, 178, 26, 20)`. O snapshot fica em
`snapshots/00094_abandoned_object.jpg`.
