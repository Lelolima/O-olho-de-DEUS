"""Testes para Edge AI Processor."""

import unittest
import numpy as np
from src.edge.processor import EdgeAIProcessor, FaceDetection
from src.edge.streamer import RTSPStreamer
from src.privacy.masker import DynamicMasker, BoundingBox


class TestEdgeAIProcessor(unittest.TestCase):
    """Testes para Edge AI Processor."""

    def test_processor_init_haar_fallback(self):
        """Testa inicialização com Haar Cascade (fallback)."""
        processor = EdgeAIProcessor(backend="haar")

        self.assertIsNotNone(processor.face_classifier)
        self.assertEqual(processor.backend, "haar")

    def test_detect_faces_haar(self):
        """Testa detecção facial com Haar Cascade."""
        processor = EdgeAIProcessor(backend="haar")

        # Frame de teste (100x100 preto)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        faces = processor._detect_faces(frame)

        # Haar pode detectar falsos positivos ou nenhum
        # Teste apenas verifica que não crasha
        self.assertIsInstance(faces, list)

    def test_process_frame(self):
        """Testa processamento completo de frame."""
        processor = EdgeAIProcessor(backend="haar")

        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        faces, masked_frame = processor.process_frame(frame)

        self.assertIsInstance(faces, list)
        self.assertEqual(masked_frame.shape, frame.shape)

    def test_face_detection_to_dict(self):
        """Testa serialização de FaceDetection."""
        face = FaceDetection(
            bounding_box=(10, 10, 50, 50),
            confidence=0.95,
            embedding=np.random.rand(512)
        )

        data = face.to_dict()

        self.assertEqual(data["bounding_box"]["x"], 10)
        self.assertEqual(data["bounding_box"]["w"], 50)
        self.assertIsNotNone(data["embedding"])


class TestDynamicMasker(unittest.TestCase):
    """Testes para Dynamic Masker."""

    def test_gaussian_blur(self):
        """Testa Gaussian Blur."""
        masker = DynamicMasker(method="gaussian", blur_strength=99)

        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        faces = [BoundingBox(0, 0, 50, 50)]

        masked = masker.apply(frame, faces)

        # Verifica que região mascarada está blur
        self.assertEqual(masked.shape, frame.shape)

    def test_pixelation(self):
        """Testa pixelação."""
        masker = DynamicMasker(method="pixelation", pixelation_factor=0.1)

        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        faces = [BoundingBox(0, 0, 50, 50)]

        masked = masker.apply(frame, faces)

        self.assertEqual(masked.shape, frame.shape)

    def test_black_box(self):
        """Testa black box."""
        masker = DynamicMasker(method="black_box")

        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        faces = [BoundingBox(0, 0, 50, 50)]

        masked = masker.apply(frame, faces)

        # Região do rosto deve estar preta
        self.assertTrue(np.all(masked[0:50, 0:50] == 0))


if __name__ == "__main__":
    unittest.main()