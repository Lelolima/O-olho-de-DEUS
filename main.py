"""
Olho de Deus v3.0 - Main Entry Point

Inicializa e roda o sistema completo:
1. Edge AI Processor (captura RTSP, detecção facial)
2. Forensic Logger (cadeia de custódia)
3. Cloud API (FastAPI para dashboard HITL)

Uso:
    python main.py --config config.yaml
"""

import argparse
import logging
import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.edge.processor import EdgeAIProcessor, create_processor_from_config
from src.edge.streamer import RTSPStreamer, MultiStreamManager
from src.forensic.logger import ForensicLogger
from src.privacy.masker import DynamicMasker
from src.fairness.metrics import FairnessMetrics, BiasDetector


def setup_logging(log_level: str = "INFO"):
    """Configura logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("olho_de_deus.log", encoding="utf-8")
        ]
    )


def load_config(config_path: str) -> dict:
    """Carrega configuração YAML/JSON."""
    import json

    path = Path(config_path)

    if not path.exists():
        # Retorna config default
        return {
            "edge": {
                "backend": "haar",  # haar, onnx, tensorrt, openvino
                "device": "CPU",
                "confidence_threshold": 0.5
            },
            "cameras": [],  # Lista de URLs RTSP
            "forensic": {
                "log_dir": "./forensic_logs",
                "tsa_enabled": True,
                "batch_size": 100
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000
            }
        }

    with open(path, "r", encoding="utf-8") as f:
        if path.suffix == ".json":
            return json.load(f)
        else:
            # YAML requer pyyaml
            import yaml
            return yaml.safe_load(f)


def run_edge_mode(config: dict):
    """
    Roda sistema em modo Edge (processamento local).

    Captura streams RTSP, processa frames, envia apenas metadados.
    """
    logger = logging.getLogger(__name__)
    logger.info("Iniciando modo Edge...")

    # Inicializa componentes
    edge_config = config.get("edge", {})
    processor = create_processor_from_config(edge_config)

    # Forensic logger
    forensic_config = config.get("forensic", {})
    forensic_logger = ForensicLogger(
        log_dir=forensic_config.get("log_dir", "./forensic_logs"),
        tsa_enabled=forensic_config.get("tsa_enabled", False),
        batch_size=forensic_config.get("batch_size", 100)
    )

    # Gerenciador de múltiplos streams
    cameras = config.get("cameras", [])
    if not cameras:
        logger.warning("Nenhuma câmera configurada")
        return

    stream_manager = MultiStreamManager(max_streams=8)

    for cam in cameras:
        stream_manager.add_stream(cam["id"], cam["url"])

    stream_manager.start_all()
    logger.info(f"{len(cameras)} streams iniciados")

    # Loop principal
    try:
        while True:
            frames = stream_manager.read_all_frames()

            for camera_id, frame in frames.items():
                if frame is None:
                    continue

                # Processa frame
                faces, masked_frame = processor.process_frame(frame)

                if faces:
                    logger.info(
                        f"[{camera_id}] {len(faces)} face(s) detectada(s)"
                    )

                    # Cria evidência
                    evidence = {
                        "id": f"evt_{camera_id}_{logger.debug}",
                        "camera_id": camera_id,
                        "timestamp": logging.getLogger().handlers[0].formatter.formatTime(
                            logging.LogRecord(
                                "", logging.INFO, "", 0, "", (), None
                            )
                        ),
                        "faces_count": len(faces),
                        "faces": [f.to_dict() for f in faces],
                        "alarm_score": 0.5  # Calcular baseado em comportamento
                    }

                    # Log forense
                    forensic_logger.log_evidence(evidence)

    except KeyboardInterrupt:
        logger.info("Parando...")
    finally:
        stream_manager.stop_all()
        forensic_logger.flush_batch()


def run_api_mode(config: dict):
    """
    Roda API Cloud (FastAPI para dashboard HITL).
    """
    import uvicorn

    api_config = config.get("api", {})

    logger = logging.getLogger(__name__)
    logger.info(f"Iniciando API em {api_config.get('host', '0.0.0.0')}:{api_config.get('port', 8000)}")

    from src.hitl.dashboard_server import app

    uvicorn.run(
        app,
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 8000)
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Olho de Deus v3.0 - Sistema de vigilância com IA"
    )

    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Caminho para arquivo de configuração"
    )

    parser.add_argument(
        "--mode", "-m",
        choices=["edge", "api", "all"],
        default="all",
        help="Modo de operação"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Nível de logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Carrega config
    config = load_config(args.config)
    logger.info(f"Configuração carregada: {args.config}")

    # Roda modo selecionado
    if args.mode == "edge":
        run_edge_mode(config)
    elif args.mode == "api":
        run_api_mode(config)
    elif args.mode == "all":
        # Roda ambos em threads separadas
        import threading

        logger.info("Iniciando modo ALL (Edge + API)...")

        # Thread para API
        api_thread = threading.Thread(
            target=run_api_mode,
            args=(config,),
            daemon=True
        )
        api_thread.start()

        # Edge na thread principal
        run_edge_mode(config)


if __name__ == "__main__":
    main()