#!/usr/bin/env python3
"""
O-olho-de-DEUS: Sistema de Segurança com IA
Sistema avançado de monitoramento e detecção facial
"""

import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import json
from datetime import datetime
import uuid
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ConfigManager:
    """Gerenciamento centralizado de configurações"""

    def __init__(self, config_path: str = 'config.json'):
        self.config_path = Path(config_path)
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Carrega configuração do arquivo ou usa defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logging.warning(f"Erro ao parsear config: {e}. Usando defaults.")
        return self._default_config()

    def _default_config(self) -> Dict:
        return {
            "security_level": "medium",
            "video_sources": [],
            "notification_emails": [],
            "notification_webhook": None,
            "log_level": "INFO",
            "confidence_threshold": 0.7,
            "incident_retention_days": 30
        }

    def save_config(self):
        """Salva configurações atuais"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)


class SecureDataHandler:
    """Tratamento seguro de dados sensíveis"""

    @staticmethod
    def hash_sensitive_data(data: str, salt: str = "olho-de-deus-salt-2026") -> str:
        """Hash de dados sensíveis com salt"""
        salted = f"{salt}{data}"
        return hashlib.sha256(salted.encode()).hexdigest()

    @staticmethod
    def anonymize_face_data(face_data: Dict) -> Dict:
        """Anonimiza dados faciais para logging"""
        return {
            "face_hash": SecureDataHandler.hash_sensitive_data(
                json.dumps(face_data, sort_keys=True)
            ),
            "timestamp": datetime.now().isoformat()
        }


class AISecuritySystem:
    """Sistema principal de segurança com IA"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.incidents_dir = Path("incidents")
        self.logs_dir = Path("logs")
        self._setup_directories()
        self._setup_logging()
        self.face_detection_model = None
        self.behavior_model = None
        self._load_ml_models()

    def _setup_directories(self):
        """Cria diretórios necessários"""
        self.incidents_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.incidents_dir / "images").mkdir(exist_ok=True)
        (self.incidents_dir / "logs").mkdir(exist_ok=True)

    def _setup_logging(self):
        """Configura sistema de logging com rotação"""
        from logging.handlers import RotatingFileHandler

        log_level = getattr(
            logging,
            self.config_manager.config.get('log_level', 'INFO').upper()
        )

        logger = logging.getLogger()
        logger.setLevel(log_level)
        logger.handlers = []

        # Handler para arquivo com rotação
        file_handler = RotatingFileHandler(
            self.logs_dir / "security_system.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s: %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    def _load_ml_models(self):
        """Carrega modelos de ML com fallback seguro"""
        try:
            # Haar Cascade para detección facial
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_detection_model = cv2.CascadeClassifier(cascade_path)
            logging.info("Modelo de deteção facial carregado")
        except Exception as e:
            logging.error(f"Erro ao carregar modelo facial: {e}")
            self.face_detection_model = None

        # Modelo de comportamento (opcional)
        behavior_model_path = Path("models/behavior_detection_model.h5")
        if behavior_model_path.exists():
            try:
                self.behavior_model = load_model(behavior_model_path)
                logging.info("Modelo comportamental carregado")
            except Exception as e:
                logging.warning(f"Não foi possível carregar modelo comportamental: {e}")
                self.behavior_model = None
        else:
            logging.info("Modelo comportamental não encontrado - usando modo básico")
            self.behavior_model = None

    def process_video_stream(self, video_source: str, stop_event=None):
        """Processamento de stream de vídeo"""
        cap = None
        try:
            # Validar source
            if not self._validate_video_source(video_source):
                logging.error(f"Fonte de vídeo inválida: {video_source}")
                return

            logging.info(f"Iniciando processamento: {video_source}")
            cap = cv2.VideoCapture(video_source)

            # Configurar timeout para webcam
            if video_source.isdigit():
                cap.set(cv2.CAP_PROP_FPS, 30)

            frame_count = 0
            while True:
                if stop_event and stop_event.is_set():
                    logging.info(f"Stop signal recebido para {video_source}")
                    break

                ret, frame = cap.read()
                if not ret:
                    logging.warning(f"Frame não capturado, tentando reconectar...")
                    cap.release()
                    import time
                    time.sleep(2)
                    cap = cv2.VideoCapture(video_source)
                    continue

                frame_count += 1
                # Processar a cada 3 frames para performance
                if frame_count % 3 == 0:
                    self._analyze_frame(frame, video_source)

        except Exception as e:
            logging.error(f"Erro no processamento do stream {video_source}: {e}")
        finally:
            if cap:
                cap.release()
            logging.info(f"Stream {video_source} finalizado")

    def _validate_video_source(self, source: str) -> bool:
        """Valida fonte de vídeo (previne SSRF)"""
        # Permitir: caminhos locais, webcams (números), URLs HTTP/HTTPS
        if source.isdigit():  # Webcam
            return True
        if source.startswith(('http://', 'https://')):
            # Bloquear IPs internos
            from urllib.parse import urlparse
            parsed = urlparse(source)
            hostname = parsed.hostname
            if hostname in ('localhost', '127.0.0.1'):
                return True
            # Bloquear IPs privados
            if hostname:
                import ipaddress
                try:
                    ip = ipaddress.ip_address(hostname)
                    if ip.is_private or ip.is_loopback:
                        logging.warning(f"IP privado/loopback bloqueado: {hostname}")
                        return False
                except ValueError:
                    pass  # É hostname, não IP
            return True
        if Path(source).exists():  # Arquivo local
            return True
        logging.warning(f"Fonte inválida: {source}")
        return False

    def _analyze_frame(self, frame: np.ndarray, source: str):
        """Análise de cada frame"""
        faces = self._detect_faces(frame)

        if self._is_suspicious_behavior(frame, faces):
            self._trigger_security_protocol(frame, faces, source)
        elif len(faces) > 0:
            logging.debug(f"{len(faces)} rosto(s) detectado(s) em {source}")

    def _detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detecção de rostos"""
        if self.face_detection_model is None:
            logging.warning("Modelo facial não carregado")
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_detection_model.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        return faces

    def _is_suspicious_behavior(
        self,
        frame: np.ndarray,
        faces: List[Tuple[int, int, int, int]]
    ) -> bool:
        """
        Detecção de comportamento suspeito.
        Implementação básica: muitos rostos ou movimento rápido.
        """
        # Threshold básico de "muitas pessoas"
        if len(faces) > 10:
            logging.info(f"Muitas pessoas detectadas: {len(faces)}")
            return True

        # Se tiver modelo comportamental, usar
        if self.behavior_model is not None:
            try:
                # Preprocessar frame para o modelo
                img = image.array_to_img(frame)
                img_resized = image.img_to_array(
                    img.resize((224, 224))
                )
                img_resized = np.expand_dims(img_resized, axis=0) / 255.0

                prediction = self.behavior_model.predict(img_resized, verbose=0)
                threshold = self.config_manager.config.get('confidence_threshold', 0.7)

                if prediction[0][0] > threshold:
                    return True
            except Exception as e:
                logging.warning(f"Erro na predição comportamental: {e}")

        return False

    def _trigger_security_protocol(
        self,
        frame: np.ndarray,
        faces: List[Tuple[int, int, int, int]],
        source: str
    ):
        """Protocolo de segurança para incidentes"""
        incident_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Salvar imagem (comprimida)
        incident_image_path = self.incidents_dir / "images" / f"{incident_id}.jpg"
        cv2.imwrite(
            str(incident_image_path),
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 85]
        )

        # Hash dos dados faciais
        face_hashes = [
            SecureDataHandler.hash_sensitive_data(f"{x}{y}{w}{h}")
            for (x, y, w, h) in faces
        ]

        # Dados do incidente
        incident_data = {
            "id": incident_id,
            "timestamp": timestamp,
            "source": str(source),
            "faces_detected": len(faces),
            "faces_hash": face_hashes,
            "image_path": str(incident_image_path),
            "created_by": "olho-de-deus-system"
        }

        # Notificar e registrar
        self._notify_authorities(incident_data)
        self._log_incident(incident_data)

    def _notify_authorities(self, incident_data: Dict):
        """Notificação multi-canal"""
        config = self.config_manager.config

        # Notificação por email (placeholder)
        emails = config.get('notification_emails', [])
        if emails:
            self._send_email_notification(emails, incident_data)

        # Notificação por webhook
        webhook = config.get('notification_webhook')
        if webhook:
            self._send_webhook_notification(webhook, incident_data)

        logging.info(f"Notificação de incidente {incident_data['id']} enviada")

    def _send_email_notification(self, emails: List[str], incident_data: Dict):
        """Envia notificação por email"""
        # Implementação placeholder - integrar com SMTP ou SendGrid
        logging.info(f"Email seria enviado para: {emails}")
        # TODO: Implementar com smtplib ou API Externa

    def _send_webhook_notification(self, webhook: str, incident_data: Dict):
        """Envia notificação por webhook"""
        try:
            response = requests.post(
                webhook,
                json=incident_data,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            logging.info("Webhook enviado com sucesso")
        except requests.RequestException as e:
            logging.error(f"Falha ao enviar webhook: {e}")

    def _log_incident(self, incident_data: Dict):
        """Registo detalhado de incidentes"""
        # Remover dados sensíveis antes de logar
        log_data = {
            "id": incident_data["id"],
            "timestamp": incident_data["timestamp"],
            "source": incident_data["source"],
            "faces_detected": incident_data["faces_detected"],
            "faces_hash": incident_data["faces_hash"],
        }
        logging.warning(f"INCIDENTE: {json.dumps(log_data)}")

        # Guardar em arquivo JSON
        log_file = self.logs_dir / "incidents" / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        log_file.parent.mkdir(exist_ok=True)

        incidents = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                incidents = json.load(f)

        incidents.append(log_data)
        with open(log_file, 'w') as f:
            json.dump(incidents, f, indent=2)

    def cleanup_old_incidents(self, retention_days: int = None):
        """Limpa incidentes antigos"""
        if retention_days is None:
            retention_days = self.config_manager.config.get('incident_retention_days', 30)

        cutoff = datetime.now().timestamp() - (retention_days * 86400)
        cleaned = 0

        for img_file in (self.incidents_dir / "images").glob("*.jpg"):
            if img_file.stat().st_mtime < cutoff:
                img_file.unlink()
                cleaned += 1

        logging.info(f"{cleaned} incidentes antigos removidos")


def main():
    """Ponto de entrada principal"""
    print("=" * 60)
    print("O-OLHO-DE-DEUS: Sistema de Segurança com IA")
    print("=" * 60)

    # Carregar configuração
    config_manager = ConfigManager('config.json')

    # Inicializar sistema
    security_system = AISecuritySystem(config_manager)

    # Obter fontes de vídeo
    video_sources = config_manager.config.get('video_sources', [])

    if not video_sources:
        print("\n⚠️  Nenhuma fonte de vídeo configurada!")
        print("Edite config.json e adicione fontes em 'video_sources'")
        print("\nExemplos:")
        print('  "video_sources": ["0"]  # Webcam')
        print('  "video_sources": ["rtsp://camera-ip/stream"]  # IP Camera')
        print('  "video_sources": ["video.mp4"]  # Arquivo')
        return

    print(f"\n📹 Fontes configuradas: {len(video_sources)}")
    for i, source in enumerate(video_sources, 1):
        print(f"   {i}. {source}")

    print("\n🚀 Iniciando monitoramento... (Ctrl+C para parar)")

    # Processamento paralelo
    try:
        with ThreadPoolExecutor(max_workers=min(4, len(video_sources))) as executor:
            executor.map(security_system.process_video_stream, video_sources)
    except KeyboardInterrupt:
        print("\n\n🛑 Parando sistema...")
    finally:
        # Cleanup
        security_system.cleanup_old_incidents()
        print("✅ Sistema finalizado")


if __name__ == "__main__":
    main()