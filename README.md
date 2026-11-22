<p align="center">
  <img src="docs/assets/banner.svg" alt="O Olho de Deus v3: analítica de vídeo na borda com privacidade, revisão humana e cadeia de custódia" width="900">
</p>

<p align="center">
  <a href="https://github.com/Lelolima/O-olho-de-DEUS/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Lelolima/O-olho-de-DEUS/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Python 3.10–3.12" src="https://img.shields.io/badge/python-3.10%E2%80%933.12-blue">
  <img alt="Licença MIT" src="https://img.shields.io/badge/licen%C3%A7a-MIT-green">
</p>

Sistema de **monitoramento de câmeras com analítica de vídeo na borda**. Ele detecta intrusão
em áreas restritas (com agenda de horário), conta pessoas que cruzam uma linha virtual,
alerta lotação e objetos abandonados, e borra rostos antes de salvar qualquer imagem. Cada
evento entra num **log forense encadeado (árvore Merkle)**. Alertas vão para uma **API de
revisão humana (HITL)** com login seguro, onde um operador decide descartar ou escalar.

**O que ele não é:** não faz reconhecimento facial nem identifica pessoas. A detecção de rosto
existe apenas para **borrar**, e embeddings faciais não são gravados nem enviados.

> A versão 2 (legada) está em [`LEGADO_v2.0.0/`](LEGADO_v2.0.0/) e no repositório
> [Project-Eyes-of-God-2.9](https://github.com/Lelolima/Project-Eyes-of-God-2.9).

## Sumário

[Arquitetura](#arquitetura) · [Instalação](#instalação) · [Configuração](#configuração) ·
[Uso](#uso) · [Exemplos](#exemplos-de-casos-reais) · [Privacidade e LGPD](#privacidade-e-lgpd) ·
[Limitações](#limitações-reais) · [Desenvolvimento](#desenvolvimento-e-qualidade)

## Arquitetura

<p align="center">
  <img src="docs/assets/arquitetura.svg" alt="Fluxo de dados: câmera → pipeline na borda → log forense e API HITL → operador → webhook" width="900">
</p>

| Camada | Módulos | Função |
|---|---|---|
| Fontes | `src/edge/sources.py`, `streamer.py` | Abre webcam (`"0"`), arquivo, `rtsp://` (FFmpeg; GStreamer se o OpenCV tiver) e `http(s)://`. Credenciais da URL nunca vão para o log |
| Pipeline | `src/edge/pipeline.py` | Frame → analisadores → eventos → log forense. Horário do evento derivado do FPS em arquivos |
| Analíticos | `src/edge/analytics.py` | `ZoneIntrusionDetector` (MOG2 + polígono + agenda), `PeopleCounter` (movimento ou **HOG do OpenCV**), `AbandonedObjectDetector` |
| Privacidade | `src/edge/processor.py`, `src/privacy/` | Detecção de rosto (Haar; ONNX opcional) só para borrar; criptografia Fernet com rotação; registro de base legal |
| Cadeia de custódia | `src/forensic/` | Lotes de evidência com raiz Merkle e prova de inclusão; carimbo RFC 3161 opcional |
| API HITL | `src/hitl/dashboard_server.py`, `src/cloud/` | FastAPI, JWT, `OPERATOR_USERS` com hash PBKDF2, limite de tentativas, alertas, evidências (SHA-256), decisões, WebSockets |
| Notificação | `src/cloud/services/notification_service.py` | Webhook (`WEBHOOK_URL`) quando um alerta é escalado ou é crítico |

## Instalação

Requer Python 3.10–3.12. Testado em 3.11 no Windows e no Ubuntu (CI).

```bash
git clone https://github.com/Lelolima/O-olho-de-DEUS.git
cd O-olho-de-DEUS
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # execução (versões fixadas)
pip install -r requirements-ci.txt   # + testes, lint e tipagem
```

<details>
<summary><b>Com Docker (API + PostgreSQL)</b></summary>

```bash
python -m src.tools.bootstrap_env --operator admin --role admin   # cria .env (pede a senha)
echo "POSTGRES_PASSWORD=<uma-senha-forte>" >> .env
docker compose up -d --build                 # API em http://127.0.0.1:8000
mkdir videos && cp sua_gravacao.mp4 videos/entrada.mp4
docker compose --profile edge up edge        # processa ./videos/entrada.mp4
```

A imagem roda como usuário não-root. A porta só é publicada em `127.0.0.1`: para acesso
externo, use um proxy reverso com TLS. Validado localmente com Docker 29: health 200, login,
alerta gravado no PostgreSQL e contêiner `healthy`.
</details>

## Configuração

### 1. Segredos e o primeiro operador

```bash
python -m src.tools.bootstrap_env --operator admin --role admin
```

O comando pede a senha (mínimo 12 caracteres, sem eco no terminal) e grava um `.env` com
`JWT_SECRET`, `ENCRYPTION_KEY` (chave Fernet) e `OPERATOR_USERS` contendo **apenas o hash
PBKDF2** da senha. Nenhum segredo é impresso. O `main.py` carrega o `.env` automaticamente;
variáveis já definidas no ambiente têm prioridade.

Para mais operadores, gere o hash com `python -m src.cloud.api.middleware.auth "<senha>"` e
acrescente ao JSON de `OPERATOR_USERS`:

```json
{"admin": {"role": "admin", "password_hash": "pbkdf2_sha256$600000$..."},
 "op1":   {"role": "operator", "password_hash": "pbkdf2_sha256$600000$..."}}
```

Sem `OPERATOR_USERS`, a API sobe, registra um aviso e o login responde **503** com a mensagem
"Nenhum operador configurado no servidor. Defina OPERATOR_USERS". Não existem usuários padrão.

<details>
<summary><b>Variáveis de ambiente</b></summary>

| Variável | Padrão | Uso |
|---|---|---|
| `OPERATOR_USERS` | — | Operadores (JSON com hashes). Obrigatória para login |
| `JWT_SECRET` | aleatório temporário | Assinatura dos tokens. Valores com menos de 32 caracteres são ignorados |
| `ENCRYPTION_KEY` | — | Chave Fernet para recortes de rosto criptografados |
| `DATABASE_URL` | vazio → SQLite `./olho_de_deus.db` | Ex.: `postgresql://olho:<senha>@host:5432/olho_de_deus` (driver psycopg 3) |
| `USE_SQLITE` | `false` | Força SQLite |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Endereço da API (prioridade sobre o config) |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens permitidas, separadas por vírgula |
| `LOGIN_RATE_PER_MINUTE` / `_PER_HOUR` | `10` / `100` | Tentativas de login por IP antes de responder 429 |
| `EVIDENCE_DIR` | `./forensic_logs` | Onde a API guarda frames de evidência |
| `EVIDENCE_MAX_MB` | `10` | Tamanho máximo de upload de evidência |
| `TSA_ENABLED` / `TSA_URL` | `false` / FreeTSA | Carimbo de tempo RFC 3161 (exige rede) |
| `WEBHOOK_URL` | — | Recebe um POST JSON quando um alerta é escalado ou é crítico |
</details>

### 2. Câmeras e analíticos (`config.yaml`)

```bash
cp config.yaml.example config.yaml
```

```yaml
cameras:
  - id: "CAM-001"
    url: "${CAM_001_URL:rtsp://192.168.1.100:554/stream1}"   # ${VAR:padrão} é expandido

analytics:                      # coordenadas normalizadas 0–1 do frame
  zone_intrusion:
    zone: [[0.0, 0.0], [0.5, 0.0], [0.5, 1.0], [0.0, 1.0]]
    active_hours: [["19:00", "07:00"]]     # só fora do expediente
  people_counter:
    line: [[0.5, 0.0], [0.5, 1.0]]         # entrada = esquerda → direita na imagem
    detector: hog                          # ou motion
    max_occupancy: 20
  abandoned_object:
    min_static_seconds: 60
```

## Uso

<p align="center">
  <img src="docs/assets/fluxo-uso.svg" alt="Fluxo de uso em 5 passos" width="900">
</p>

```bash
python main.py -c config.yaml -m api                       # API HITL (docs em /docs)
python main.py -c config.yaml -m edge                      # todas as câmeras do config
python main.py -c config.yaml -m edge -s gravacao.mp4      # um arquivo ou webcam ("0")
python main.py -c config.yaml -m all                       # API em segundo plano + edge
python -m src.cloud.init_db                                # cria as tabelas
```

No modo edge, cada câmera roda numa thread. Ao terminar, o comando imprime um resumo JSON
(`frames_processed`, `events_by_type`...). Códigos de saída: `0` ok, `1` fonte indisponível,
`2` nenhuma câmera configurada.

<details>
<summary><b>Endpoints da API</b> (todos exigem <code>Authorization: Bearer &lt;token&gt;</code>, exceto login, <code>/</code> e <code>/health</code>)</summary>

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/auth/token` | Login (form `username`, `password`) → JWT. 401 se inválido, 429 em excesso, 503 sem operadores |
| POST | `/api/v1/alerts/` | Cria alerta: score ≥ 0,95 é escalado e notificado; ≥ 0,70 fica pendente para HITL |
| GET | `/api/v1/alerts/` · `/api/v1/alerts/{id}` | Lista / consulta |
| POST | `/api/v1/alerts/{id}/review` | Revisão (`dismiss` / `escalate`) |
| POST | `/api/v1/hitl/review` | Decisão HITL. O operador vem do token, não do corpo |
| GET | `/api/v1/hitl/decisions/{alert_id}` · `/operators/{id}/stats` · `/dashboard/summary` | Auditoria e painel |
| POST | `/api/v1/evidence/upload` | Envia frame (máx. `EVIDENCE_MAX_MB`) e calcula SHA-256 |
| POST | `/api/v1/evidence/{id}/verify` | Recalcula o hash e detecta adulteração |
| WS | `/api/v1/alerts/ws/live?token=` · `/api/v1/hitl/ws/queue?token=` | Tempo real. Sem token válido, fecha com código 1008 |

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/token -d "username=admin" --data-urlencode "password=$SENHA" | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/v1/alerts/
```
</details>

## Exemplos de casos reais

Cada exemplo é executável e tem README próprio (problema, como rodar, saída esperada). Sem
`--video`, ele gera uma cena sintética; com `--video`, usa a sua gravação. Os quatro rodam no CI.

| Exemplo | Caso | Resultado na cena de amostra |
|---|---|---|
| [01 — Intrusão fora do horário](examples/01_intrusao_fora_do_horario/) | movimento no pátio entre 19h e 7h | 22:30 → 1 alerta · 10:00 → nenhum |
| [02 — Contagem e lotação](examples/02_contagem_de_pessoas/) | entradas/saídas por uma porta | 3 entradas, 1 saída, alerta ao passar de 2 |
| [03 — Objeto abandonado](examples/03_objeto_abandonado/) | mala deixada no saguão | 1 alerta, caixa sobre a mala |
| [04 — Fluxo HITL completo](examples/04_fluxo_hitl_completo/) | evento → alerta → login → revisão → evidência verificada | escalado, evidência íntegra, Merkle válido |

```bash
python examples/01_intrusao_fora_do_horario/run.py
python examples/02_contagem_de_pessoas/run.py --video gravacao.mp4 --detector hog --hog-resize 1.5
```

<details>
<summary><b>O que foi validado com dados reais (e o que não foi)</b></summary>

- **Detector HOG de pessoas** (OpenCV, CPU) no vídeo público `vtest.avi` (768×576): ~6 pessoas/frame
  com `hog_resize=1.5`. Num frame conferido visualmente: 6 acertos, 1 falso positivo (uma van),
  2 pessoas perdidas (uma distante, outra encoberta). Custo: 0,13–0,34 s/frame.
- **Borramento de rosto** (Haar) na foto pública `messi5.jpg`: o rosto principal foi borrado;
  rostos minúsculos da torcida (< 30 px) não foram.
- **API + PostgreSQL em Docker**: login, alerta persistido, healthcheck.
- **Não validado:** câmera física, RTSP real, modelos ONNX (YOLOv8-Face/FaceNet; o código aceita,
  mas nenhum peso foi testado) e acurácia de contagem contra uma referência manual.
</details>

## Privacidade e LGPD

Imagens de pessoas são dados pessoais. Usar o sistema exige base legal (em geral, legítimo
interesse ou segurança, art. 7º da LGPD), transparência e minimização. O software ajuda nisso,
mas **não substitui** a análise jurídica e o relatório de impacto (RIPD) do controlador.

- **Aviso de monitoramento:** sinalize as áreas filmadas com placas visíveis antes da entrada,
  indicando o controlador, a finalidade (segurança patrimonial) e um contato do encarregado (DPO).
- **Minimização:** rostos são borrados nos snapshots e nas evidências gerados pelo pipeline.
  Não há reconhecimento facial nem embeddings gravados. Os eventos guardam tipo, horário,
  câmera e caixas delimitadoras.
- **Acesso restrito:** todas as rotas de dados exigem login. Senhas ficam só como hash PBKDF2,
  há limite de tentativas, e cada decisão HITL é registrada com o operador do token. Hoje todos
  os operadores autenticados têm o mesmo acesso: os papéis (`role`) ficam registrados, mas
  ainda não restringem rotas.
- **Revisão humana:** alertas abaixo de 0,95 dependem de decisão de um operador antes de
  qualquer notificação externa.
- **Retenção:** defina um prazo (ex.: 30 dias para gravações sem incidente) e aplique-o ao
  diretório de evidências e ao banco. O projeto **não apaga dados automaticamente**: a
  eliminação precisa equilibrar a LGPD com a cadeia de custódia de incidentes e é decisão do
  controlador. `LegalBasisRegistry` (`src/privacy/legal_basis.py`) registra finalidade, base
  legal e prazo de cada tratamento.
- **Direitos dos titulares:** mantenha um canal para pedidos de acesso e eliminação. Os logs
  forenses permitem localizar eventos por câmera e horário.

## Limitações reais

- Analíticos clássicos (MOG2/HOG) erram com chuva, sombras fortes, mudanças bruscas de luz e
  multidões. Pessoas muito próximas viram um único blob no detector `motion`.
- O detector de objeto abandonado também dispara para uma pessoa parada pelo mesmo tempo.
- A detecção de rosto por Haar perde rostos pequenos, de perfil ou parcialmente cobertos. O
  borramento é um esforço de minimização, não uma garantia.
- `verify_timestamp` confere o hash e a presença do certificado da TSA, mas **não valida a
  assinatura** criptográfica da resposta RFC 3161.
- Envio por **e-mail e SMS não está implementado** (retorna `success: false`); o webhook está.
- O dashboard web (frontend) não existe neste repositório; a API tem documentação interativa em `/docs`.
- Papéis de operador ainda não restringem rotas.

## Desenvolvimento e qualidade

```bash
pip install -r requirements-ci.txt
USE_SQLITE=true python -m pytest -q --cov=src      # 116 testes, cobertura de 76% (mínimo de 70% no CI)
ruff check src tests main.py examples && ruff format --check src tests main.py examples
mypy src/edge src/forensic src/privacy src/tools src/envfile.py src/cloud/api/middleware/auth.py main.py \
     --ignore-missing-imports --follow-imports=silent
```

O CI (`.github/workflows/ci.yml`) roda lint, formatação, mypy, os testes (que incluem os 4
exemplos) e o build da imagem Docker. Não publica nada e não faz deploy. Auditorias:
[`docs/auditoria/`](docs/auditoria/) e [`docs/auditoria-seguranca-vies.md`](docs/auditoria-seguranca-vies.md).

<details>
<summary><b>Problemas comuns</b></summary>

- **`ModuleNotFoundError: yaml`**: instale `requirements.txt` (o PyYAML faz parte dele).
- **Login responde 503**: defina `OPERATOR_USERS` (veja [Configuração](#configuração)).
- **Login responde 429**: excesso de tentativas pelo mesmo IP; aguarde ou ajuste `LOGIN_RATE_PER_MINUTE`.
- **RTSP não conecta**: confira a URL com `ffplay`/VLC. Os wheels do PyPI usam FFmpeg; GStreamer só se o seu OpenCV foi compilado com ele.
- **Nenhum alerta de intrusão**: a zona só fica ativa no horário de `active_hours`; para arquivos, o horário vem de `--inicio` nos exemplos ou do momento da execução no `main.py`.
- **HOG não detecta pessoas pequenas**: aumente `hog_resize` (1.5–2.0), ao custo de mais CPU.
</details>

## Licença e contato

MIT. Verifique as leis locais antes de qualquer implantação.
Desenvolvido por Wellington de Lima Catarina — lelolima806@gmail.com.
