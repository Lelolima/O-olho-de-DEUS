"""
Edge AI Processor - Processamento de vídeo na borda com TensorRT/OpenVINO.

Este módulo implementa processamento de frames na borda (edge computing),
extraindo apenas metadados e embeddings sem enviar vídeo bruto para nuvem.

Arquitetura:
1. Captura RTSP/WebRTC → GStreamer
2. Detecção facial → YOLOv8-Face / Haar Cascade
3. Extração embedding → FaceNet / ArcFace (512-dim)
4. Dynamic Masking → Gaussian Blur (σ=99)
5. Saída: Metadados JSON + frame mascarado
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    """Detecção facial com embedding."""

    bounding_box: Tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float
    embedding: Optional[np.ndarray] = None  # 512-dim vector
    embedding_model: str = "unknown"
    masked: bool = True
    landmark: Optional[List[Tuple[int, int]]] = None  # 5 pontos faciais

    def to_dict(self) -> dict:
        """Serializa para dict JSON-serializable."""
        return {
            "bounding_box": {
                "x": self.bounding_box[0],
                "y": self.bounding_box[1],
                "w": self.bounding_box[2],
                "h": self.bounding_box[3]
            },
            "confidence": self.confidence,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "embedding_dim": self.embedding.shape[0] if self.embedding is not None else 0,
            "embedding_model": self.embedding_model,
            "masked": self.masked,
            "landmarks": self.landmark
        }


class EdgeAIProcessor:
    """
    Processador de Edge AI para detecção facial e extração de embeddings.

    Suporta backends:
    - TensorRT (NVIDIA GPUs)
    - OpenVINO (Intel CPUs/GPUs)
    - ONNX Runtime (CPU fallback)
    - OpenCV Haar Cascade (fallback mínimo)

    Uso:
        processor = EdgeAIProcessor(
            face_model_path="models/yolov8-face.onnx",
            embedding_model_path="models/facenet.onnx",
            backend="onnx"  # "tensorrt", "openvino", "onnx", "haar"
        )

        faces, masked_frame = processor.process_frame(frame)
    """

    # Backends suportados
    TENSORRT = "tensorrt"
    OPENVINO = "openvino"
    ONNX = "onnx"
    HAAR = "haar"

    def __init__(
        self,
        face_model_path: Optional[str] = None,
        embedding_model_path: Optional[str] = None,
        backend: str = ONNX,
        device: str = "GPU",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45
    ):
        """
        Inicializa Edge AI Processor.

        Args:
            face_model_path: Caminho para modelo de detecção facial
            embedding_model_path: Caminho para modelo de embedding
            backend: Backend de inferência ("tensorrt", "openvino", "onnx", "haar")
            device: Dispositivo ("GPU", "CPU", "MYSQL")
            confidence_threshold: Threshold mínimo para detecções
            iou_threshold: Threshold para Non-Maximum Suppression
        """
        self.face_model_path = face_model_path
        self.embedding_model_path = embedding_model_path
        self.backend = backend
        self.device = device
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold

        # Modelos carregados
        self.face_model = None
        self.embedding_model = None
        self.face_classifier = None  # Haar Cascade fallback

        # Session de inferência
        self.face_session = None
        self.embedding_session = None

        # Carrega modelos
        self._load_models()

    def _load_models(self):
        """Carrega modelos de detecção e embedding."""
        logger.info(f"Carregando modelos com backend: {self.backend}")

        # Carrega detector facial
        if self.backend == self.HAAR or not self.face_model_path:
            # Fallback: Haar Cascade
            self.face_classifier = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            logger.info("Haar Cascade carregado como fallback")
        else:
            # Carrega modelo ONNX/TensorRT/OpenVINO
            self._load_face_model()

        # Carrega modelo de embedding
        if self.embedding_model_path:
            self._load_embedding_model()

    def _load_face_model(self):
        """Carrega modelo de detecção facial."""
        try:
            if self.backend == self.ONNX:
                import onnxruntime as ort

                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                self.face_session = ort.InferenceSession(
                    self.face_model_path,
                    providers=providers if self.device == "GPU" else ["CPUExecutionProvider"]
                )
                logger.info(f"Modelo facial ONNX carregado: {self.face_model_path}")

            elif self.backend == self.TENSORRT:
                # TensorRT requer instalação específica
                try:
                    from tensorrt import Runtime, Logger

                    logger_trt = Logger()
                    with open(self.face_model_path, "rb") as f:
                        engine_data = f.read()

                    runtime = Runtime(logger_trt)
                    self.face_model = runtime.deserialize_cuda_engine(engine_data)
                    logger.info(f"Modelo facial TensorRT carregado")

                except ImportError:
                    logger.warning("TensorRT não disponível, fallback para ONNX")
                    self.backend = self.ONNX
                    self._load_face_model()

            elif self.backend == self.OPENVINO:
                try:
                    from openvino.runtime import Core

                    core = Core()
                    self.face_model = core.read_model(self.face_model_path)
                    self.face_session = core.compile_model(self.face_model, self.device)
                    logger.info(f"Modelo facial OpenVINO carregado")

                except ImportError:
                    logger.warning("OpenVINO não disponível, fallback para ONNX")
                    self.backend = self.ONNX
                    self._load_face_model()

        except Exception as e:
            logger.error(f"Erro ao carregar modelo facial: {e}")
            # Fallback para Haar
            self.backend = self.HAAR
            self.face_classifier = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

    def _load_embedding_model(self):
        """Carrega modelo de extração de embeddings."""
        try:
            if self.backend == self.ONNX:
                import onnxruntime as ort

                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                self.embedding_session = ort.InferenceSession(
                    self.embedding_model_path,
                    providers=providers if self.device == "GPU" else ["CPUExecutionProvider"]
                )
                logger.info(f"Modelo de embedding ONNX carregado")

            elif self.backend == self.TENSORRT:
                # Similar ao face model, mas para embedding
                try:
                    from tensorrt import Runtime, Logger

                    logger_trt = Logger()
                    with open(self.embedding_model_path, "rb") as f:
                        engine_data = f.read()

                    runtime = Runtime(logger_trt)
                    self.embedding_model = runtime.deserialize_cuda_engine(engine_data)

                except ImportError:
                    logger.warning("TensorRT não disponível para embedding")
                    self.embedding_session = None

        except Exception as e:
            logger.warning(f"Erro ao carregar modelo de embedding: {e}")
            self.embedding_session = None

    def process_frame(
        self,
        frame: np.ndarray,
        extract_embedding: bool = True
    ) -> Tuple[List[FaceDetection], np.ndarray]:
        """
        Processa frame na borda.

        Args:
            frame: Frame BGR (OpenCV format)
            extract_embedding: Se True, extrai embedding para cada face

        Returns:
            Tuple com:
            - Lista de FaceDetection
            - Frame com masking aplicado (todos os rostos borrados)
        """
        # Step 1: Detecta faces
        faces = self._detect_faces(frame)

        # Step 2: Extrai embeddings (opcional)
        if extract_embedding and self.embedding_session:
            for face in faces:
                face.embedding = self._extract_embedding(frame, face.bounding_box)

        # Step 3: Aplica masking em todos os rostos
        masked_frame = self._apply_masking(frame, faces)

        return faces, masked_frame

    def _detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detecta faces no frame."""
        if self.backend == self.HAAR or self.face_classifier is not None:
            return self._detect_faces_haar(frame)
        elif self.backend == self.ONNX:
            return self._detect_faces_onnx(frame)
        elif self.backend == self.TENSORRT:
            return self._detect_faces_tensorrt(frame)
        elif self.backend == self.OPENVINO:
            return self._detect_faces_openvino(frame)
        else:
            return []

    def _detect_faces_haar(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detecção usando Haar Cascade (fallback)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces_rects = self.face_classifier.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        faces = []
        for (x, y, w, h) in faces_rects:
            faces.append(FaceDetection(
                bounding_box=(x, y, w, h),
                confidence=0.7,  # Haar não dá confiança precisa
                embedding_model="none"
            ))

        return faces

    def _detect_faces_onnx(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detecção usando modelo ONNX (YOLOv8-Face)."""
        if not self.face_session:
            return self._detect_faces_haar(frame)

        # Preprocess
        input_tensor = self._preprocess_frame(frame)

        # Inferência
        outputs = self.face_session.run(None, {self.face_session.get_inputs()[0].name: input_tensor})

        # Post-process
        faces = self._postprocess_detection(outputs, frame.shape)

        return faces

    def _detect_faces_tensorrt(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detecção usando TensorRT."""
        if not self.face_model:
            return self._detect_faces_haar(frame)

        # Implementação específica TensorRT
        # Requer context de inferência e buffers CUDA
        logger.warning("Inferência TensorRT não implementada completa")
        return self._detect_faces_haar(frame)

    def _detect_faces_openvino(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detecção usando OpenVINO."""
        if not self.face_session:
            return self._detect_faces_haar(frame)

        # Preprocess
        input_tensor = self._preprocess_frame(frame)

        # Inferência
        result = self.face_session.infer({self.face_session.input(0): input_tensor})

        # Post-process
        faces = self._postprocess_detection([result], frame.shape)

        return faces

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocessa frame para inferência."""
        # Resize para input do modelo (ex: 640x640 para YOLOv8)
        input_size = (640, 640)

        resized = cv2.resize(frame, input_size)
        normalized = resized.astype(np.float32) / 255.0

        # HWC para CHW
        if len(normalized.shape) == 3:
            normalized = np.transpose(normalized, (2, 0, 1))

        # Adiciona batch dimension
        return np.expand_dims(normalized, axis=0)

    def _postprocess_detection(
        self,
        outputs: list,
        frame_shape: tuple
    ) -> List[FaceDetection]:
        """Processa outputs da detecção."""
        faces = []

        # YOLOv8-Face output: [batch, 84, 8400] ou similar
        # Precisa de NMS para filtrar

        output = outputs[0] if isinstance(outputs, list) else outputs

        # Implementação simplificada
        # Em produção, implementar NMS completo

        if len(output.shape) >= 3:
            # Output típico YOLO: (1, num_boxes, 15) ou (1, 84, 8400)
            if output.shape[1] > output.shape[2]:
                output = np.transpose(output, (0, 2, 1))

            # Extrai boxes e confianças
            # Formato: [x, y, w, h, confidence, class_probs, ...landmarks]
            for det in output[0]:
                confidence = float(det[4])

                if confidence >= self.confidence_threshold:
                    x, y, w, h = det[0:4]

                    # Converte para coordenadas absolutas
                    x = int(x * frame_shape[1])
                    y = int(y * frame_shape[0])
                    w = int(w * frame_shape[1])
                    h = int(h * frame_shape[0])

                    faces.append(FaceDetection(
                        bounding_box=(x, y, w, h),
                        confidence=confidence,
                        embedding_model="pending"
                    ))

        return faces

    def _extract_embedding(
        self,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """Extrai embedding facial (512-dim)."""
        if not self.embedding_session:
            return np.zeros(512)

        x, y, w, h = bbox

        # Extrai ROI
        roi = frame[y:y+h, x:x+w]
        if roi.size == 0:
            return np.zeros(512)

        # Preprocess para FaceNet
        roi_resized = cv2.resize(roi, (160, 160))  # FaceNet input
        roi_normalized = roi_resized.astype(np.float32) / 255.0

        # Standardization (FaceNet)
        mean = np.mean(roi_normalized)
        std = np.std(roi_normalized)
        if std > 0:
            roi_normalized = (roi_normalized - mean) / std

        input_tensor = np.expand_dims(roi_normalized, axis=0)

        # Inferência
        output = self.embedding_session.run(
            None,
            {self.embedding_session.get_inputs()[0].name: input_tensor}
        )

        # Retorna embedding normalizado
        embedding = output[0].flatten()
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _apply_masking(
        self,
        frame: np.ndarray,
        faces: List[FaceDetection]
    ) -> np.ndarray:
        """Aplica blur em todos os rostos detectados."""
        from src.privacy.masker import DynamicMasker, BoundingBox

        masker = DynamicMasker(method="gaussian", blur_strength=99)

        # Converte para BoundingBox
        boxes = [
            BoundingBox(
                x=f.bounding_box[0],
                y=f.bounding_box[1],
                width=f.bounding_box[2],
                height=f.bounding_box[3]
            )
            for f in faces
        ]

        return masker.apply(frame, boxes)

    def get_model_info(self) -> dict:
        """Retorna informações sobre modelos carregados."""
        return {
            "backend": self.backend,
            "device": self.device,
            "face_model_loaded": self.face_session is not None or self.face_classifier is not None,
            "embedding_model_loaded": self.embedding_session is not None,
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold
        }


def create_processor_from_config(config: dict) -> EdgeAIProcessor:
    """
    Factory function para criar EdgeAIProcessor de config.

    Config schema:
    {
        "backend": "onnx",  # "tensorrt", "openvino", "onnx", "haar"
        "device": "GPU",
        "models": {
            "face": "models/yolov8-face.onnx",
            "embedding": "models/facenet.onnx"
        },
        "thresholds": {
            "confidence": 0.5,
            "iou": 0.45
        }
    }
    """
    return EdgeAIProcessor(
        face_model_path=config.get("models", {}).get("face"),
        embedding_model_path=config.get("models", {}).get("embedding"),
        backend=config.get("backend", "onnx"),
        device=config.get("device", "GPU"),
        confidence_threshold=config.get("thresholds", {}).get("confidence", 0.5),
        iou_threshold=config.get("thresholds", {}).get("iou", 0.45)
    )