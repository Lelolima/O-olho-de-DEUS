"""
Olho de Deus v3 - ponto de entrada.

Modos:
    edge  processa câmeras (ou um arquivo de vídeo com --source) na borda
    api   sobe a API HITL (FastAPI) para operadores
    all   API em segundo plano + edge

Exemplos:
    python main.py --config config.yaml --mode api
    python main.py --config config.yaml --mode edge --source video.mp4 --max-frames 500
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "edge": {"backend": "haar", "device": "CPU", "thresholds": {"confidence": 0.5}},
    "cameras": [],
    "forensic": {"log_dir": "./forensic_logs", "tsa_enabled": False, "batch_size": 100},
    "api": {"host": "127.0.0.1", "port": 8000},
    "logging": {"level": "INFO", "file": None},
}

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}")

logger = logging.getLogger("olho_de_deus")


def expand_env(value: Any) -> Any:
    """Expande ``${VAR}`` e ``${VAR:padrão}`` recursivamente (strings em dict/list)."""
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(2) or ""), value)
    if isinstance(value, dict):
        return {k: expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v) for v in value]
    return value


def load_config(config_path: str | None) -> dict[str, Any]:
    """Carrega YAML/JSON. Sem arquivo, usa ``DEFAULT_CONFIG`` (com aviso)."""
    if not config_path or not Path(config_path).exists():
        if config_path:
            logger.warning(f"Arquivo de configuração não encontrado: {config_path}; usando padrões")
        defaults: dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))
        return defaults

    path = Path(config_path)
    with path.open(encoding="utf-8") as fh:
        if path.suffix.lower() == ".json":
            data = json.load(fh)
        else:
            import yaml

            data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuração inválida em {config_path}: esperado um mapeamento")
    expanded: dict[str, Any] = expand_env(data)
    return expanded


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )


def build_pipeline(config: dict[str, Any], camera_id: str):
    """Monta o ``VideoPipeline`` a partir da configuração."""
    from src.edge.pipeline import VideoPipeline
    from src.edge.processor import create_processor_from_config
    from src.forensic.logger import ForensicLogger

    edge_cfg = config.get("edge", {})
    processor = None
    if edge_cfg.get("face_detection", True):
        processor = create_processor_from_config(edge_cfg)

    forensic_cfg = config.get("forensic", {})
    forensic_logger = ForensicLogger(
        log_dir=forensic_cfg.get("log_dir", "./forensic_logs"),
        tsa_enabled=bool(forensic_cfg.get("tsa_enabled", False)),
        tsa_url=forensic_cfg.get("tsa_url") or None,
        batch_size=int(forensic_cfg.get("batch_size", 100)),
    )

    return VideoPipeline(
        camera_id=camera_id,
        analyzers=[],
        processor=processor,
        forensic_logger=forensic_logger,
        face_event_min_faces=int(edge_cfg.get("face_event_min_faces", 1)),
    )


def run_edge_mode(config: dict[str, Any], source: str | None = None, max_frames: int | None = None) -> int:
    """Processa ``--source`` ou as câmeras do config. Retorna código de saída."""
    from src.edge.sources import VideoSourceError, redact_url

    cameras = [{"id": "CLI", "url": source}] if source is not None else config.get("cameras") or []
    if not cameras:
        logger.error("Nenhuma câmera configurada (seção 'cameras' do config) e nenhum --source informado")
        return 2

    results: dict[str, Any] = {}
    errors: list[str] = []

    def worker(cam: dict[str, Any]) -> None:
        cam_id = str(cam.get("id", "CAM"))
        try:
            pipeline = build_pipeline(config, cam_id)
            summary = pipeline.run(cam["url"], max_frames=max_frames)
            results[cam_id] = summary.to_dict()
            logger.info(f"[{cam_id}] concluído: {summary.to_dict()}")
        except (VideoSourceError, ConnectionError, KeyError) as exc:
            errors.append(cam_id)
            logger.error(f"[{cam_id}] fonte {redact_url(str(cam.get('url')))} indisponível: {exc}")

    threads = [threading.Thread(target=worker, args=(cam,), daemon=True) for cam in cameras]
    for t in threads:
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
        return 130

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if errors and not results else 0


def run_api_mode(config: dict[str, Any]) -> int:
    import uvicorn

    from src.hitl.dashboard_server import app

    api_cfg = config.get("api", {})
    host = api_cfg.get("host", "127.0.0.1")
    port = int(api_cfg.get("port", 8000))
    logger.info(f"Iniciando API em {host}:{port}")
    uvicorn.run(app, host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Olho de Deus v3 - monitoramento de vídeo com IA na borda")
    parser.add_argument("--config", "-c", default="config.yaml", help="arquivo YAML/JSON de configuração")
    parser.add_argument("--mode", "-m", choices=["edge", "api", "all"], default="all", help="modo de operação")
    parser.add_argument("--source", "-s", help="fonte única: arquivo de vídeo, índice de webcam ou URL rtsp/http")
    parser.add_argument("--max-frames", type=int, default=None, help="limite de frames por fonte")
    parser.add_argument("--log-level", default=None, help="DEBUG, INFO, WARNING, ERROR")
    parser.add_argument("--env-file", default=".env", help="arquivo .env a carregar (padrão: .env)")
    args = parser.parse_args(argv)

    from src.envfile import load_env_file

    load_env_file(args.env_file)

    setup_logging(args.log_level or "INFO")
    config = load_config(args.config)
    log_cfg = config.get("logging", {})
    setup_logging(args.log_level or log_cfg.get("level", "INFO"), log_cfg.get("file"))

    if args.mode == "edge":
        return run_edge_mode(config, args.source, args.max_frames)
    if args.mode == "api":
        return run_api_mode(config)

    threading.Thread(target=run_api_mode, args=(config,), daemon=True).start()
    return run_edge_mode(config, args.source, args.max_frames)


if __name__ == "__main__":
    sys.exit(main())
