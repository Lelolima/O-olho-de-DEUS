"""
Dynamic Masker - Anonimização dinâmica de rostos (Privacy by Design).

Este módulo implementa blur em tempo real de rostos detectados,
garantindo que nenhumm rosto de inocente seja visível no stream
de vídeo ou nas evidências armazenadas, exceto quando:
1. Score de alarme > 98% (alta confiança de crime)
2. Operador HITL valida a desofuscação

A violação de privacidade é prevenida na fonte (borda), não apenas
na transmissão.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class BoundingBox:
    """Bounding box de face detectada."""

    x: int
    y: int
    width: int
    height: int

    @property
    def tuple(self) -> Tuple[int, int, int, int]:
        """Retorna como tupla (x, y, w, h)."""
        return (self.x, self.y, self.width, self.height)

    @property
    def slice(self) -> Tuple[slice, slice]:
        """Retorna slices para numpy indexing [y:y+h, x:x+w]."""
        return (
            slice(self.y, self.y + self.height),
            slice(self.x, self.x + self.width)
        )

    def expand(self, margin: int) -> 'BoundingBox':
        """Expande bounding box por margem (clamped à imagem)."""
        return BoundingBox(
            x=max(0, self.x - margin),
            y=max(0, self.y - margin),
            width=self.width + 2 * margin,
            height=self.height + 2 * margin
        )


class DynamicMasker:
    """
    Aplica mascaramento dinâmico em rostos detectados.

    Estratégias de mascaramento:
    - Gaussian Blur: Borramento forte (σ=99)
    - Pixelation: Reduz resolução e escala de volta
    - Black Box: Retângulo preto sólido

    Uso:
        masker = DynamicMasker(method="gaussian")
        masked_frame = masker.apply(frame, faces)
    """

    # Métodos de mascaramento
    GAUSSIAN = "gaussian"
    PIXELATION = "pixelation"
    BLACK_BOX = "black_box"

    def __init__(
        self,
        method: str = GAUSSIAN,
        blur_strength: int = 99,
        pixelation_factor: float = 0.1,
        expand_margin: int = 10
    ):
        """
        Inicializa DynamicMasker.

        Args:
            method: Método de mascaramento ("gaussian", "pixelation", "black_box")
            blur_strength: Força do Gaussian Blur (deve ser ímpar, >= 3)
            pixelation_factor: Fator de pixelação (0.01-0.5, menor = mais pixelado)
            expand_margin: Margem de expansão do bounding box (pixels)
        """
        self.method = method

        # Valida blur_strength (deve ser ímpar para OpenCV)
        if blur_strength % 2 == 0:
            blur_strength += 1
        self.blur_strength = max(3, blur_strength)

        self.pixelation_factor = max(0.01, min(0.5, pixelation_factor))
        self.expand_margin = expand_margin

    def apply(
        self,
        frame: np.ndarray,
        faces: List[BoundingBox]
    ) -> np.ndarray:
        """
        Aplica mascaramento em todos os rostos detectados.

        Args:
            frame: Frame BGR (OpenCV format)
            faces: Lista de BoundingBox de rostos

        Returns:
            Frame com rostos mascarados
        """
        if not faces:
            return frame.copy()

        masked = frame.copy()

        for face in faces:
            # Expande bounding box para incluir cabelo/queixo
            expanded = face.expand(self.expand_margin)

            # Aplica método selecionado
            if self.method == self.GAUSSIAN:
                masked_region = self._gaussian_blur(frame, expanded)
            elif self.method == self.PIXELATION:
                masked_region = self._pixelate(frame, expanded)
            elif self.method == self.BLACK_BOX:
                masked_region = self._black_box(expanded, frame.shape)
            else:
                masked_region = self._gaussian_blur(frame, expanded)

            # Substitui região no frame
            y_slice, x_slice = expanded.slice
            # Clamp slices to frame bounds
            y_slice = slice(
                max(0, y_slice.start),
                min(frame.shape[0], y_slice.stop)
            )
            x_slice = slice(
                max(0, x_slice.start),
                min(frame.shape[1], x_slice.stop)
            )

            # Adjust masked_region if clamping occurred
            y_offset = max(0, y_slice.start) - expanded.y
            x_offset = max(0, x_slice.start) - expanded.x
            region = masked_region[
                y_offset:y_offset + y_slice.stop - y_slice.start,
                x_offset:x_offset + x_slice.stop - x_slice.start
            ]

            masked[y_slice, x_slice] = region

        return masked

    def _gaussian_blur(
        self,
        frame: np.ndarray,
        face: BoundingBox
    ) -> np.ndarray:
        """Aplica Gaussian Blur forte no rosto."""
        y_slice, x_slice = face.slice

        # Extrai ROI
        roi = frame[y_slice, x_slice].copy()

        # Garante que kernel seja ímpar e caiba na ROI
        kernel_size = min(self.blur_strength, roi.shape[0] - 1, roi.shape[1] - 1)
        if kernel_size % 2 == 0:
            kernel_size -= 1
        kernel_size = max(3, kernel_size)

        # Sigma alto = blur forte
        sigma = self.blur_strength  # σ=99 para ofuscação total

        blurred = cv2.GaussianBlur(roi, (kernel_size, kernel_size), sigma)
        return blurred

    def _pixelate(
        self,
        frame: np.ndarray,
        face: BoundingBox
    ) -> np.ndarray:
        """
        Aplica pixelação no rosto.

        Reduz a ROI para pequena resolução e escala de volta,
        criando efeito de "pixel art".
        """
        y_slice, x_slice = face.slice
        roi = frame[y_slice, x_slice].copy()

        h, w = roi.shape[:2]

        # Calcula tamanho reduzido
        small_h = max(1, int(h * self.pixelation_factor))
        small_w = max(1, int(w * self.pixelation_factor))

        # Reduz e escala de volta
        small = cv2.resize(
            roi,
            (small_w, small_h),
            interpolation=cv2.INTER_AREA
        )
        pixelated = cv2.resize(
            small,
            (w, h),
            interpolation=cv2.INTER_NEAREST
        )

        return pixelated

    def _black_box(
        self,
        face: BoundingBox,
        frame_shape: tuple
    ) -> np.ndarray:
        """Cria retângulo preto sólido."""
        y_slice, x_slice = face.slice

        # Calcula dimensões após clamping
        h = min(frame_shape[0], y_slice.stop) - max(0, y_slice.start)
        w = min(frame_shape[1], x_slice.stop) - max(0, x_slice.start)

        # Retorna black box
        if len(frame_shape) == 3:
            return np.zeros((h, w, frame_shape[2]), dtype=np.uint8)
        else:
            return np.zeros((h, w), dtype=np.uint8)


class ConditionalUnblurer:
    """
    Desofuscação condicional de rostos com duas chaves.

    Sistema de verificação dupla:
    1. Chave técnica: alarm_score >= 0.98 (98% confiança)
    2. Chave humana: operador HITL precisa autorizar explicitamente

    Isso previne:
    - Exposição acidental de rostos de inocentes
    - Violação de privacidade por falsos positivos
    - Acesso não autorizado a imagens sensíveis
    """

    # Threshold mínimo de confiança para permitir desofuscação
    MIN_CONFIDENCE_THRESHOLD = 0.98

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Inicializa ConditionalUnblurer.

        Args:
            encryption_key: Chave para criptografia Fernet.
                           Se None, usa modo simulação (sem criptografia real).
        """
        self.encryption_key = encryption_key

        if encryption_key:
            from cryptography.fernet import Fernet
            self.fernet = Fernet(encryption_key)
        else:
            self.fernet = None

    def encrypt_face_roi(
        self,
        face_roi: np.ndarray,
        output_format: str = "png"
    ) -> bytes:
        """
        Criptografa ROI do rosto antes de enviar para nuvem.

        Args:
            face_roi: Região do rosto (BGR)
            output_format: Formato de encoding ("png", "jpeg")

        Returns:
            ROI criptografada como bytes
        """
        # Codifica imagem
        if output_format == "jpeg":
            _, buffer = cv2.imencode(".jpeg", face_roi, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            _, buffer = cv2.imencode(".png", face_roi)

        plaintext = buffer.tobytes()

        # Criptografa
        if self.fernet:
            return self.fernet.encrypt(plaintext)
        else:
            # Modo simulação: retorna base64
            import base64
            return b"UNENCRYPTED:" + base64.b64encode(plaintext)

    def decrypt_face_roi(
        self,
        encrypted_roi: bytes,
        alarm_score: float,
        hitl_approved: bool
    ) -> Optional[np.ndarray]:
        """
        Descriptografa ROI SOMENTE se ambas condições forem satisfeitas:
        1. alarm_score >= 0.98 (98% confiança)
        2. hitl_approved == True (operador validou)

        Args:
            encrypted_roi: ROI criptografada
            alarm_score: Score de alarme da IA (0-1)
            hitl_approved: True se operador HITL validou

        Returns:
            ROI descriptografada como numpy array, ou None se não autorizado

        Raises:
            PermissionError: Se condições não forem satisfeitas
        """
        # Verifica chave técnica
        if alarm_score < self.MIN_CONFIDENCE_THRESHOLD:
            raise PermissionError(
                f"Confiança insuficiente para desofuscação: "
                f"{alarm_score:.2f} < {self.MIN_CONFIDENCE_THRESHOLD}"
            )

        # Verifica chave humana
        if not hitl_approved:
            raise PermissionError(
                "Validação humana (HITL) requerida para desofuscação"
            )

        # Descriptografa
        if self.fernet and not encrypted_roi.startswith(b"UNENCRYPTED:"):
            plaintext = self.fernet.decrypt(encrypted_roi)
        else:
            # Modo simulação ou não criptografado
            import base64
            if encrypted_roi.startswith(b"UNENCRYPTED:"):
                plaintext = base64.b64decode(encrypted_roi[12:])
            else:
                plaintext = encrypted_roi

        # Decodifica imagem
        buffer = np.frombuffer(plaintext, dtype=np.uint8)
        face = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

        return face

    def can_unblur(self, alarm_score: float, hitl_approved: bool) -> tuple[bool, str]:
        """
        Verifica se pode desofuscar sem levantar exceção.

        Args:
            alarm_score: Score de alarme (0-1)
            hitl_approved: True se operador validou

        Returns:
            (pode_desofuscar, motivo)
        """
        if alarm_score < self.MIN_CONFIDENCE_THRESHOLD:
            return False, f"Score {alarm_score:.2f} abaixo de {self.MIN_CONFIDENCE_THRESHOLD}"

        if not hitl_approved:
            return False, "Aguardando validação HITL"

        return True, "Autorizado"


def create_blurred_preview(
    frame: np.ndarray,
    faces: List[BoundingBox],
    preview_size: Tuple[int, int] = (320, 240)
) -> bytes:
    """
    Cria preview borrado para dashboard HITL.

    O preview mostra o frame com blur aplicado em todos os rostos,
    permitindo que o operador avalie o contexto sem expor identidades.

    Args:
        frame: Frame original
        faces: Lista de bounding boxes
        preview_size: Tamanho do preview (largura, altura)

    Returns:
        Preview como JPEG bytes (para envio ao frontend)
    """
    # Redimensiona para preview
    resized = cv2.resize(frame, preview_size)

    # Ajusta bounding boxes para escala
    scale_x = preview_size[0] / frame.shape[1]
    scale_y = preview_size[1] / frame.shape[0]

    scaled_faces = [
        BoundingBox(
            x=int(f.x * scale_x),
            y=int(f.y * scale_y),
            width=int(f.width * scale_x),
            height=int(f.height * scale_y)
        )
        for f in faces
    ]

    # Aplica blur
    masker = DynamicMasker(method="gaussian", blur_strength=50)
    blurred = masker.apply(resized, scaled_faces)

    # Codifica como JPEG
    _, buffer = cv2.imencode(".jpeg", blurred, [cv2.IMWRITE_JPEG_QUALITY, 80])

    return buffer.tobytes()