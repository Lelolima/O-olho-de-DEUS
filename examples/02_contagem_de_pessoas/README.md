# 02 — Contagem de pessoas e alerta de lotação

**Problema:** uma loja precisa saber quantas pessoas entraram e saíram por uma porta, e ser
avisada quando a ocupação passar do limite.

**Como funciona:** `PeopleCounter` rastreia objetos e conta o cruzamento de uma linha virtual
(vertical no meio da imagem: **entrada** = esquerda→direita). Quando
`entradas − saídas > lotação`, gera `occupancy_exceeded`. A detecção pode usar:

- `--detector motion` (padrão): blobs de movimento (MOG2). Rápido, mas pessoas muito próximas viram um blob só.
- `--detector hog`: detector de pessoas HOG + SVM **que vem com o OpenCV** (modelo real, sem download).
  A janela tem 128 px de altura; para pessoas pequenas/distantes use `--hog-resize 1.5`.

## Como rodar

```bash
python examples/02_contagem_de_pessoas/run.py
python examples/02_contagem_de_pessoas/run.py --lotacao 5
python examples/02_contagem_de_pessoas/run.py --video vtest.avi --detector hog --hog-resize 1.5
```

## Saída esperada

Cena sintética (3 pessoas entram, 1 sai, lotação 2), valores reais:

```json
{"entradas": 3, "saidas": 1, "ocupacao_final": 2,
 "events_by_type": {"line_crossing": 4, "occupancy_exceeded": 1}}
```

Vídeo real de pedestres `vtest.avi` (amostra pública do OpenCV, 768×576, 795 frames;
**não** incluído no repositório; validado localmente em 2026-11-22):

- `--detector hog` sem ampliação: ~1,2 pessoa/frame detectada (perde quem tem menos de ~128 px).
- `--hog-resize 1.5`: ~6 pessoas/frame, coerente com a cena. Num frame conferido visualmente:
  6 acertos, 1 falso positivo (uma van) e 2 pessoas perdidas (uma distante, outra encoberta por uma placa).
- Custo em CPU: ~0,13 s/frame (1,0×) e ~0,34 s/frame (1,5×).

Os números de entradas/saídas no vídeo real **não** foram comparados com uma contagem manual
de referência; trate-os como demonstração, não como acurácia medida.
