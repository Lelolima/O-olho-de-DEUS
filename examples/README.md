# Exemplos de casos reais

Cada pasta tem um `run.py` executável e um README curto (problema, como rodar, saída esperada).
Todos rodam em CPU, sem câmera e sem downloads: sem `--video`, geram uma cena sintética
(`src/tools/sample_videos.py`). Com `--video`, processam o seu arquivo. O CI executa os quatro
(`tests/examples/test_examples.py`).

| Exemplo | Caso | Técnica |
|---|---|---|
| [01_intrusao_fora_do_horario](01_intrusao_fora_do_horario/) | movimento em área restrita só entre 19h e 7h | MOG2 + polígono + agenda |
| [02_contagem_de_pessoas](02_contagem_de_pessoas/) | entradas/saídas por linha virtual e lotação | blobs de movimento ou HOG do OpenCV |
| [03_objeto_abandonado](03_objeto_abandonado/) | mala deixada no saguão | primeiro plano estático persistente |
| [04_fluxo_hitl_completo](04_fluxo_hitl_completo/) | evento → alerta → login → revisão → evidência verificada | pipeline + API + Merkle |

```bash
pip install -r requirements-ci.txt
python examples/01_intrusao_fora_do_horario/run.py --saida /tmp/ex01
```

Para gerar só os vídeos de amostra:

```bash
python -m src.tools.sample_videos --scene intrusao --out intrusao.avi   # ou contagem / abandono
```

Nenhum exemplo identifica pessoas. Não há reconhecimento facial no projeto, apenas detecção
de rosto para **borrar**.
